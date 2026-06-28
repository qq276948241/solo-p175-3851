from marshmallow import Schema, fields, validate, validates, ValidationError


class DoctorCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50, error='医生姓名长度需在1-50字之间'))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20, error='电话长度不能超过20位'))
    specialty = fields.Str(allow_none=True, validate=validate.Length(max=200, error='专长描述长度不能超过200字'))
    is_active = fields.Bool(allow_none=True, load_default=True)


class DoctorUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=50, error='医生姓名长度需在1-50字之间'))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20, error='电话长度不能超过20位'))
    specialty = fields.Str(allow_none=True, validate=validate.Length(max=200, error='专长描述长度不能超过200字'))
    is_active = fields.Bool(allow_none=True)


class AvailableSlotsQuerySchema(Schema):
    doctor_id = fields.Int(required=True, validate=validate.Range(min=1, error='医生ID不正确'))
    date = fields.Str(required=True, error='请指定查询日期')
