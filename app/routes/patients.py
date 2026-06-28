from flask import Blueprint, request
from marshmallow import ValidationError
from sqlalchemy import or_

from app import db
from app.models.patient import Patient
from app.schemas.patient import PatientCreateSchema, PatientUpdateSchema, PatientQuerySchema
from app.utils.errors import ApiException, success_response

bp = Blueprint('patients', __name__)


@bp.route('/patients', methods=['POST'])
def create_patient():
    schema = PatientCreateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise e

    existing = Patient.query.filter_by(phone=data['phone']).first()
    if existing:
        raise ApiException('该手机号已注册，请直接使用', 400)

    patient = Patient(
        name=data['name'],
        phone=data['phone'],
        gender=data.get('gender'),
        age=data.get('age'),
        address=data.get('address'),
        medical_history=data.get('medical_history')
    )
    db.session.add(patient)
    db.session.commit()

    return success_response(patient.to_dict(), '患者建档成功')


@bp.route('/patients', methods=['GET'])
def get_patients():
    schema = PatientQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        raise e

    query = Patient.query

    if params.get('name'):
        query = query.filter(Patient.name.like(f'%{params["name"]}%'))
    if params.get('phone'):
        query = query.filter(Patient.phone.like(f'%{params["phone"]}%'))

    page = params['page']
    page_size = params['page_size']
    total = query.count()
    pagination = query.order_by(Patient.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )

    data = {
        'total': total,
        'page': page,
        'page_size': page_size,
        'list': [p.to_dict() for p in pagination.items]
    }
    return success_response(data, '查询成功')


@bp.route('/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        raise ApiException('患者不存在', 404)
    return success_response(patient.to_dict(), '查询成功')


@bp.route('/patients/phone/<phone>', methods=['GET'])
def get_patient_by_phone(phone):
    patient = Patient.query.filter_by(phone=phone).first()
    if not patient:
        raise ApiException('未找到该手机号对应的患者', 404)
    return success_response(patient.to_dict(), '查询成功')


@bp.route('/patients/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        raise ApiException('患者不存在', 404)

    schema = PatientUpdateSchema()
    try:
        data = schema.load(request.get_json() or {}, partial=True)
    except ValidationError as e:
        raise e

    if 'phone' in data and data['phone'] != patient.phone:
        existing = Patient.query.filter_by(phone=data['phone']).first()
        if existing:
            raise ApiException('该手机号已被其他患者使用', 400)

    if 'name' in data:
        patient.name = data['name']
    if 'phone' in data:
        patient.phone = data['phone']
    if 'gender' in data:
        patient.gender = data['gender']
    if 'age' in data:
        patient.age = data['age']
    if 'address' in data:
        patient.address = data['address']
    if 'medical_history' in data:
        patient.medical_history = data['medical_history']

    db.session.commit()
    return success_response(patient.to_dict(), '患者信息更新成功')


@bp.route('/patients/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        raise ApiException('患者不存在', 404)

    if patient.appointments:
        raise ApiException('该患者存在预约记录，无法删除', 400)

    db.session.delete(patient)
    db.session.commit()
    return success_response(None, '患者删除成功')
