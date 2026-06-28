import re
from marshmallow import Schema, fields, validate, validates, ValidationError


class MedicalRecordCreateSchema(Schema):
    patient_id = fields.Int(required=True, validate=validate.Range(min=1, error='患者ID不正确'))
    doctor_id = fields.Int(required=True, validate=validate.Range(min=1, error='医生ID不正确'))
    appointment_id = fields.Int(allow_none=True, validate=validate.Range(min=1, error='预约ID不正确'))
    visit_date = fields.Str(allow_none=True, error='请指定就诊日期')
    diagnosis = fields.Str(allow_none=True, validate=validate.Length(max=2000, error='诊断内容长度不能超过2000字'))
    treatment = fields.Str(allow_none=True, validate=validate.Length(max=2000, error='治疗方案长度不能超过2000字'))
    prescription = fields.Str(allow_none=True, validate=validate.Length(max=1000, error='处方长度不能超过1000字'))
    fees = fields.Float(allow_none=True, load_default=0, validate=validate.Range(min=0, error='费用不能为负数'))
    notes = fields.Str(allow_none=True, validate=validate.Length(max=2000, error='备注长度不能超过2000字'))

    @validates('visit_date')
    def validate_date(self, value):
        if value and not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            raise ValidationError('日期格式不正确，应为YYYY-MM-DD')


class MedicalRecordUpdateSchema(Schema):
    diagnosis = fields.Str(allow_none=True, validate=validate.Length(max=2000, error='诊断内容长度不能超过2000字'))
    treatment = fields.Str(allow_none=True, validate=validate.Length(max=2000, error='治疗方案长度不能超过2000字'))
    prescription = fields.Str(allow_none=True, validate=validate.Length(max=1000, error='处方长度不能超过1000字'))
    fees = fields.Float(allow_none=True, validate=validate.Range(min=0, error='费用不能为负数'))
    notes = fields.Str(allow_none=True, validate=validate.Length(max=2000, error='备注长度不能超过2000字'))
    visit_date = fields.Str(allow_none=True)

    @validates('visit_date')
    def validate_date(self, value):
        if value and not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            raise ValidationError('日期格式不正确，应为YYYY-MM-DD')


class MedicalRecordQuerySchema(Schema):
    patient_id = fields.Int(allow_none=True)
    doctor_id = fields.Int(allow_none=True)
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)
    page = fields.Int(allow_none=True, load_default=1, validate=validate.Range(min=1, error='页码必须大于0'))
    page_size = fields.Int(allow_none=True, load_default=20, validate=validate.Range(min=1, max=200, error='每页数量需在1-200之间'))


class ExportQuerySchema(Schema):
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)
    patient_id = fields.Int(allow_none=True)
    doctor_id = fields.Int(allow_none=True)
