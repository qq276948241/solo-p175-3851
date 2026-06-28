from datetime import datetime
from flask import Blueprint, request
from marshmallow import ValidationError

from app import db
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.schemas.medical_record import (
    MedicalRecordCreateSchema, MedicalRecordUpdateSchema, MedicalRecordQuerySchema
)
from app.utils.errors import ApiException, success_response
from app.utils.business import parse_date

bp = Blueprint('records', __name__)


@bp.route('/records', methods=['POST'])
def create_record():
    schema = MedicalRecordCreateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    patient = Patient.query.get(data['patient_id'])
    if not patient:
        raise ApiException('患者不存在', 404)

    doctor = Doctor.query.get(data['doctor_id'])
    if not doctor:
        raise ApiException('医生不存在', 404)

    appointment = None
    if data.get('appointment_id'):
        appointment = Appointment.query.get(data['appointment_id'])
        if not appointment:
            raise ApiException('关联预约不存在', 404)
        if appointment.patient_id != patient.id:
            raise ApiException('预约患者与记录患者不一致', 400)

    visit_date = None
    if data.get('visit_date'):
        visit_date = parse_date(data['visit_date'])
        if not visit_date:
            raise ApiException('就诊日期格式不正确', 400)
    else:
        visit_date = datetime.now().date()

    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_id=appointment.id if appointment else None,
        visit_date=visit_date,
        diagnosis=data.get('diagnosis'),
        treatment=data.get('treatment'),
        prescription=data.get('prescription'),
        fees=data.get('fees', 0),
        notes=data.get('notes')
    )
    db.session.add(record)

    if appointment and appointment.status != 'completed':
        appointment.status = 'completed'

    db.session.commit()
    return success_response(record.to_dict(), '诊疗记录创建成功')


@bp.route('/records', methods=['GET'])
def get_records():
    schema = MedicalRecordQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        raise e

    query = MedicalRecord.query

    if params.get('patient_id'):
        query = query.filter_by(patient_id=params['patient_id'])
    if params.get('doctor_id'):
        query = query.filter_by(doctor_id=params['doctor_id'])
    if params.get('start_date'):
        sd = parse_date(params['start_date'])
        if sd:
            query = query.filter(MedicalRecord.visit_date >= sd)
    if params.get('end_date'):
        ed = parse_date(params['end_date'])
        if ed:
            query = query.filter(MedicalRecord.visit_date <= ed)

    page = params['page']
    page_size = params['page_size']
    total = query.count()
    pagination = query.order_by(
        MedicalRecord.visit_date.desc(),
        MedicalRecord.created_at.desc()
    ).paginate(page=page, per_page=page_size, error_out=False)

    data = {
        'total': total,
        'page': page,
        'page_size': page_size,
        'list': [r.to_dict() for r in pagination.items]
    }
    return success_response(data, '查询成功')


@bp.route('/records/<int:record_id>', methods=['GET'])
def get_record(record_id):
    record = MedicalRecord.query.get(record_id)
    if not record:
        raise ApiException('诊疗记录不存在', 404)
    return success_response(record.to_dict(), '查询成功')


@bp.route('/records/patient/<int:patient_id>', methods=['GET'])
def get_patient_records(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        raise ApiException('患者不存在', 404)

    records = MedicalRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(
        MedicalRecord.visit_date.desc(),
        MedicalRecord.created_at.desc()
    ).all()

    total_fees = sum(float(r.fees or 0) for r in records)
    data = {
        'patient': patient.to_dict(),
        'total_visits': len(records),
        'total_fees': total_fees,
        'records': [r.to_dict() for r in records]
    }
    return success_response(data, '查询成功')


@bp.route('/records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    record = MedicalRecord.query.get(record_id)
    if not record:
        raise ApiException('诊疗记录不存在', 404)

    schema = MedicalRecordUpdateSchema()
    try:
        data = schema.load(request.get_json() or {}, partial=True)
    except ValidationError as e:
        raise e

    if 'diagnosis' in data:
        record.diagnosis = data['diagnosis']
    if 'treatment' in data:
        record.treatment = data['treatment']
    if 'prescription' in data:
        record.prescription = data['prescription']
    if 'fees' in data:
        record.fees = data['fees']
    if 'notes' in data:
        record.notes = data['notes']
    if 'visit_date' in data and data['visit_date']:
        vd = parse_date(data['visit_date'])
        if vd:
            record.visit_date = vd

    db.session.commit()
    return success_response(record.to_dict(), '诊疗记录更新成功')


@bp.route('/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    record = MedicalRecord.query.get(record_id)
    if not record:
        raise ApiException('诊疗记录不存在', 404)

    db.session.delete(record)
    db.session.commit()
    return success_response(None, '诊疗记录删除成功')
