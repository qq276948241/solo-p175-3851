from flask import Blueprint, request
from marshmallow import ValidationError

from app import db
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.schemas.doctor import DoctorCreateSchema, DoctorUpdateSchema, AvailableSlotsQuerySchema
from app.utils.errors import ApiException, success_response
from app.utils.business import is_business_day, get_available_slots, parse_date, is_weekend

bp = Blueprint('doctors', __name__)


@bp.route('/doctors', methods=['POST'])
def create_doctor():
    schema = DoctorCreateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    doctor = Doctor(
        name=data['name'],
        phone=data.get('phone'),
        specialty=data.get('specialty'),
        is_active=data.get('is_active', True)
    )
    db.session.add(doctor)
    db.session.commit()

    return success_response(doctor.to_dict(), '医生创建成功')


@bp.route('/doctors', methods=['GET'])
def get_doctors():
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    query = Doctor.query
    if active_only:
        query = query.filter_by(is_active=True)

    doctors = query.order_by(Doctor.id).all()
    data = [d.to_dict() for d in doctors]
    return success_response(data, '查询成功')


@bp.route('/doctors/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        raise ApiException('医生不存在', 404)
    return success_response(doctor.to_dict(), '查询成功')


@bp.route('/doctors/<int:doctor_id>', methods=['PUT'])
def update_doctor(doctor_id):
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        raise ApiException('医生不存在', 404)

    schema = DoctorUpdateSchema()
    try:
        data = schema.load(request.get_json() or {}, partial=True)
    except ValidationError as e:
        raise e

    if 'name' in data:
        doctor.name = data['name']
    if 'phone' in data:
        doctor.phone = data['phone']
    if 'specialty' in data:
        doctor.specialty = data['specialty']
    if 'is_active' in data:
        doctor.is_active = data['is_active']

    db.session.commit()
    return success_response(doctor.to_dict(), '医生信息更新成功')


@bp.route('/doctors/<int:doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        raise ApiException('医生不存在', 404)

    if doctor.appointments:
        raise ApiException('该医生存在预约记录，无法删除', 400)

    db.session.delete(doctor)
    db.session.commit()
    return success_response(None, '医生删除成功')


@bp.route('/doctors/available-slots', methods=['GET'])
def get_available_slots_api():
    schema = AvailableSlotsQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        raise e

    doctor = Doctor.query.get(params['doctor_id'])
    if not doctor:
        raise ApiException('医生不存在', 404)
    if not doctor.is_active:
        raise ApiException('该医生已停诊', 400)

    target_date = parse_date(params['date'])
    if not target_date:
        raise ApiException('日期格式不正确，应为YYYY-MM-DD', 400)

    if not is_business_day(target_date):
        return success_response({
            'date': params['date'],
            'doctor_id': doctor.id,
            'doctor_name': doctor.name,
            'is_business_day': False,
            'weekend': is_weekend(target_date),
            'slots': [],
            'note': '周三全天休息'
        }, '查询成功')

    booked_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == target_date,
        Appointment.status.in_(['pending', 'confirmed'])
    ).all()
    booked_times = [a.appointment_time for a in booked_appointments]

    slots = get_available_slots(doctor.id, target_date, booked_times)

    data = {
        'date': params['date'],
        'doctor_id': doctor.id,
        'doctor_name': doctor.name,
        'is_business_day': True,
        'weekend': is_weekend(target_date),
        'slots': slots,
        'total_available': len([s for s in slots if s['available']]),
        'total_booked': len(booked_times)
    }
    return success_response(data, '查询成功')


@bp.route('/doctors/schedule', methods=['GET'])
def get_doctors_schedule():
    date_str = request.args.get('date')
    if not date_str:
        raise ApiException('请指定查询日期', 400)

    target_date = parse_date(date_str)
    if not target_date:
        raise ApiException('日期格式不正确，应为YYYY-MM-DD', 400)

    if not is_business_day(target_date):
        doctors = Doctor.query.filter_by(is_active=True).all()
        return success_response({
            'date': date_str,
            'is_business_day': False,
            'weekend': is_weekend(target_date),
            'note': '周三全天休息',
            'doctors': [
                {
                    'doctor_id': d.id,
                    'doctor_name': d.name,
                    'specialty': d.specialty,
                    'appointments': []
                } for d in doctors
            ]
        }, '查询成功')

    doctors = Doctor.query.filter_by(is_active=True).all()
    result = []

    for doctor in doctors:
        appts = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == target_date,
            Appointment.status != 'cancelled'
        ).order_by(Appointment.appointment_time).all()

        booked_appts = [a for a in appts if a.status in ['pending', 'confirmed']]
        booked_times = [a.appointment_time for a in booked_appts]
        slots = get_available_slots(doctor.id, target_date, booked_times)

        result.append({
            'doctor_id': doctor.id,
            'doctor_name': doctor.name,
            'specialty': doctor.specialty,
            'appointments': [a.to_dict() for a in appts],
            'available_slots': slots,
            'total_available': len([s for s in slots if s['available']]),
            'total_booked': len(booked_times)
        })

    data = {
        'date': date_str,
        'is_business_day': True,
        'weekend': is_weekend(target_date),
        'doctors': result
    }
    return success_response(data, '查询成功')
