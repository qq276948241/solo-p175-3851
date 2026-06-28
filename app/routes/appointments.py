from datetime import datetime
from flask import Blueprint, request
from marshmallow import ValidationError

from app import db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.schemas.appointment import (
    AppointmentCreateSchema, AppointmentRescheduleSchema,
    AppointmentUpdateStatusSchema, AppointmentQuerySchema
)
from app.utils.errors import ApiException, success_response
from app.utils.business import (
    is_business_day, validate_time_slot, parse_date,
    get_available_slots, is_thursday_afternoon
)

bp = Blueprint('appointments', __name__)


@bp.route('/appointments', methods=['POST'])
def create_appointment():
    schema = AppointmentCreateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    patient = Patient.query.get(data['patient_id'])
    if not patient:
        raise ApiException('患者不存在', 404)

    if patient.is_blacklisted():
        raise ApiException('该患者已被列入黑名单，暂无法新预约，请联系前台', 400)

    doctor = Doctor.query.get(data['doctor_id'])
    if not doctor:
        raise ApiException('医生不存在', 404)
    if not doctor.is_active:
        raise ApiException('该医生已停诊，无法预约', 400)

    target_date = parse_date(data['appointment_date'])
    if not target_date:
        raise ApiException('日期格式不正确', 400)

    if not is_business_day(target_date):
        raise ApiException('周三全天休息，请选择其他日期', 400)

    if is_thursday_afternoon(target_date, data['appointment_time']):
        raise ApiException('周四下午诊所举办健康讲座，暂停新预约，请选择上午或其他日期', 400)

    if not validate_time_slot(data['appointment_time'], target_date):
        raise ApiException('预约时段不在营业时间范围内，营业时间：9:00-12:00，13:00-18:00', 400)

    existing_patient_same_day = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == target_date,
        Appointment.status.in_(['pending', 'confirmed', 'completed'])
    ).first()
    if existing_patient_same_day:
        raise ApiException('同一患者不能在同一天重复预约同一医生', 400)

    existing_slot = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == target_date,
        Appointment.appointment_time == data['appointment_time'],
        Appointment.status.in_(['pending', 'confirmed'])
    ).first()
    if existing_slot:
        raise ApiException('该时段已被预约，请选择其他时间', 400)

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=target_date,
        appointment_time=data['appointment_time'],
        chief_complaint=data.get('chief_complaint'),
        notes=data.get('notes'),
        status=data.get('status', 'pending')
    )
    db.session.add(appointment)
    db.session.commit()

    return success_response(appointment.to_dict(), '预约成功')


@bp.route('/appointments', methods=['GET'])
def get_appointments():
    schema = AppointmentQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        raise e

    query = Appointment.query

    if params.get('patient_id'):
        query = query.filter_by(patient_id=params['patient_id'])
    if params.get('doctor_id'):
        query = query.filter_by(doctor_id=params['doctor_id'])
    if params.get('status'):
        query = query.filter_by(status=params['status'])
    if params.get('start_date'):
        sd = parse_date(params['start_date'])
        if sd:
            query = query.filter(Appointment.appointment_date >= sd)
    if params.get('end_date'):
        ed = parse_date(params['end_date'])
        if ed:
            query = query.filter(Appointment.appointment_date <= ed)

    page = params['page']
    page_size = params['page_size']
    total = query.count()
    pagination = query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time
    ).paginate(page=page, per_page=page_size, error_out=False)

    data = {
        'total': total,
        'page': page,
        'page_size': page_size,
        'list': [a.to_dict() for a in pagination.items]
    }
    return success_response(data, '查询成功')


@bp.route('/appointments/<int:appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        raise ApiException('预约不存在', 404)
    return success_response(appointment.to_dict(), '查询成功')


@bp.route('/appointments/<int:appointment_id>/reschedule', methods=['PUT'])
def reschedule_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        raise ApiException('预约不存在', 404)

    if appointment.status == 'completed':
        raise ApiException('已完成的预约无法改约', 400)
    if appointment.status == 'cancelled':
        raise ApiException('已取消的预约无法改约', 400)
    if appointment.status == 'no_show':
        raise ApiException('已标记未到诊的预约无法改约', 400)

    schema = AppointmentRescheduleSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    target_date = parse_date(data['appointment_date'])
    if not target_date:
        raise ApiException('日期格式不正确', 400)

    if not is_business_day(target_date):
        raise ApiException('周三全天休息，请选择其他日期', 400)

    if not validate_time_slot(data['appointment_time'], target_date):
        raise ApiException('新时段不在营业时间范围内', 400)

    existing_slot = Appointment.query.filter(
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.appointment_date == target_date,
        Appointment.appointment_time == data['appointment_time'],
        Appointment.status.in_(['pending', 'confirmed']),
        Appointment.id != appointment.id
    ).first()
    if existing_slot:
        raise ApiException('该时段已被预约，请选择其他时间', 400)

    existing_patient_same_day = Appointment.query.filter(
        Appointment.patient_id == appointment.patient_id,
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.appointment_date == target_date,
        Appointment.status.in_(['pending', 'confirmed', 'completed']),
        Appointment.id != appointment.id
    ).first()
    if existing_patient_same_day:
        raise ApiException('同一患者不能在同一天重复预约同一医生', 400)

    old_info = f'原预约：{appointment.appointment_date.strftime("%Y-%m-%d")} {appointment.appointment_time}'
    appointment.appointment_date = target_date
    appointment.appointment_time = data['appointment_time']
    if data.get('notes'):
        appointment.notes = (appointment.notes + '\n' if appointment.notes else '') + data['notes']
    appointment.notes = (appointment.notes + '\n' if appointment.notes else '') + f'[改约记录] {old_info} → {data["appointment_date"]} {data["appointment_time"]}'

    db.session.commit()
    return success_response(appointment.to_dict(), '改约成功')


@bp.route('/appointments/<int:appointment_id>/status', methods=['PUT'])
def update_appointment_status(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        raise ApiException('预约不存在', 404)

    schema = AppointmentUpdateStatusSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    old_status = appointment.status
    new_status = data['status']

    if old_status != new_status:
        if new_status == 'no_show':
            patient = Patient.query.get(appointment.patient_id)
            if patient:
                patient.record_no_show()
        elif new_status == 'completed' and old_status != 'no_show':
            patient = Patient.query.get(appointment.patient_id)
            if patient:
                patient.record_fulfill()

    appointment.status = new_status
    if data.get('notes'):
        status_text_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'completed': '已完成',
            'cancelled': '已取消',
            'no_show': '未到诊'
        }
        status_text = status_text_map.get(data['status'], data['status'])
        appointment.notes = (appointment.notes + '\n' if appointment.notes else '') + f'[状态变更] {status_text}：{data["notes"]}'

    db.session.commit()
    return success_response(appointment.to_dict(), f'预约状态已更新为{appointment.get_status_text()}')


@bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        raise ApiException('预约不存在', 404)

    json_data = request.get_json() or {}

    if 'chief_complaint' in json_data:
        if len(json_data['chief_complaint'] or '') > 200:
            raise ApiException('主诉长度不能超过200字', 400)
        appointment.chief_complaint = json_data['chief_complaint']
    if 'notes' in json_data:
        if len(json_data['notes'] or '') > 500:
            raise ApiException('备注长度不能超过500字', 400)
        appointment.notes = json_data['notes']

    db.session.commit()
    return success_response(appointment.to_dict(), '预约信息更新成功')


@bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        raise ApiException('预约不存在', 404)

    if appointment.status == 'completed':
        raise ApiException('已完成的预约无法取消', 400)
    if appointment.status == 'cancelled':
        raise ApiException('预约已取消，无需重复操作', 400)
    if appointment.status == 'no_show':
        raise ApiException('已标记未到诊的预约无法取消', 400)

    appointment.status = 'cancelled'
    db.session.commit()
    return success_response(appointment.to_dict(), '预约已取消')
