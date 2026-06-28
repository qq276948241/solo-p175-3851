from datetime import datetime
from flask import Blueprint, request
from marshmallow import ValidationError

from app.schemas.appointment import (
    AppointmentCreateSchema, AppointmentRescheduleSchema,
    AppointmentUpdateStatusSchema, AppointmentQuerySchema
)
from app.utils.errors import success_response
from app.utils.business import parse_date
from app.services.appointment_service import AppointmentService
from app.models.appointment import Appointment

bp = Blueprint('appointments', __name__)


@bp.route('/appointments', methods=['POST'])
def create_appointment():
    schema = AppointmentCreateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    appointment = AppointmentService.create_appointment(data)
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
    appointment = AppointmentService.get_appointment_or_404(appointment_id)
    return success_response(appointment.to_dict(), '查询成功')


@bp.route('/appointments/<int:appointment_id>/reschedule', methods=['PUT'])
def reschedule_appointment(appointment_id):
    schema = AppointmentRescheduleSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    appointment = AppointmentService.reschedule_appointment(appointment_id, data)
    return success_response(appointment.to_dict(), '改约成功')


@bp.route('/appointments/<int:appointment_id>/status', methods=['PUT'])
def update_appointment_status(appointment_id):
    schema = AppointmentUpdateStatusSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    appointment = AppointmentService.update_appointment_status(appointment_id, data)
    return success_response(appointment.to_dict(), f'预约状态已更新为{appointment.get_status_text()}')


@bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    json_data = request.get_json() or {}
    appointment = AppointmentService.update_appointment_info(appointment_id, json_data)
    return success_response(appointment.to_dict(), '预约信息更新成功')


@bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    appointment = AppointmentService.cancel_appointment(appointment_id)
    return success_response(appointment.to_dict(), '预约已取消')


@bp.route('/appointments/available', methods=['GET'])
def get_available_appointments():
    doctor_id = request.args.get('doctor_id', type=int)
    date_str = request.args.get('date')

    result = AppointmentService.get_available_slots(doctor_id, date_str)
    return success_response(result, '查询成功')
