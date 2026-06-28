import re
from marshmallow import Schema, fields, validate, validates, ValidationError


VALID_STATUSES = ['pending', 'confirmed', 'completed', 'cancelled', 'no_show', 'doctor_reschedule', 'patient_cancel']


class AppointmentCreateSchema(Schema):
    patient_id = fields.Int(required=True, validate=validate.Range(min=1, error='患者ID不正确'))
    doctor_id = fields.Int(required=True, validate=validate.Range(min=1, error='医生ID不正确'))
    appointment_date = fields.Str(required=True, error='请指定预约日期')
    appointment_time = fields.Str(required=True, error='请指定预约时段')
    chief_complaint = fields.Str(allow_none=True, validate=validate.Length(max=200, error='主诉长度不能超过200字'))
    notes = fields.Str(allow_none=True, validate=validate.Length(max=500, error='备注长度不能超过500字'))
    status = fields.Str(allow_none=True, load_default='pending', validate=validate.OneOf(
        VALID_STATUSES, error='状态值不正确'
    ))

    @validates('appointment_date')
    def validate_date(self, value):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            raise ValidationError('日期格式不正确，应为YYYY-MM-DD')

    @validates('appointment_time')
    def validate_time(self, value):
        if not re.match(r'^\d{2}:\d{2}$', value):
            raise ValidationError('时间格式不正确，应为HH:MM')


class AppointmentRescheduleSchema(Schema):
    appointment_date = fields.Str(required=True, error='请指定新的预约日期')
    appointment_time = fields.Str(required=True, error='请指定新的预约时段')
    notes = fields.Str(allow_none=True, validate=validate.Length(max=500, error='备注长度不能超过500字'))

    @validates('appointment_date')
    def validate_date(self, value):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            raise ValidationError('日期格式不正确，应为YYYY-MM-DD')

    @validates('appointment_time')
    def validate_time(self, value):
        if not re.match(r'^\d{2}:\d{2}$', value):
            raise ValidationError('时间格式不正确，应为HH:MM')


class AppointmentUpdateStatusSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(
        VALID_STATUSES, error='状态值不正确，可选值：pending/confirmed/completed/cancelled/no_show/doctor_reschedule/patient_cancel'
    ))
    notes = fields.Str(allow_none=True, validate=validate.Length(max=500, error='备注长度不能超过500字'))


class AppointmentQuerySchema(Schema):
    patient_id = fields.Int(allow_none=True)
    doctor_id = fields.Int(allow_none=True)
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    page = fields.Int(allow_none=True, load_default=1, validate=validate.Range(min=1, error='页码必须大于0'))
    page_size = fields.Int(allow_none=True, load_default=20, validate=validate.Range(min=1, max=200, error='每页数量需在1-200之间'))
