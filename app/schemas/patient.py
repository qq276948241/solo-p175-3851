import re
from marshmallow import Schema, fields, validate, validates, ValidationError


class PatientCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50, error='姓名长度需在1-50字之间'))
    phone = fields.Str(required=True, validate=validate.Length(min=11, max=20, error='手机号长度不正确'))
    gender = fields.Str(allow_none=True, validate=validate.OneOf(['男', '女', '其他'], error='性别只能是男/女/其他'))
    age = fields.Int(allow_none=True, validate=validate.Range(min=0, max=150, error='年龄范围不正确'))
    address = fields.Str(allow_none=True, validate=validate.Length(max=200, error='地址长度不能超过200字'))
    medical_history = fields.Str(allow_none=True, validate=validate.Length(max=1000, error='病史备注长度不能超过1000字'))

    @validates('phone')
    def validate_phone(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise ValidationError('手机号格式不正确，请输入11位有效手机号')


class PatientUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=50, error='姓名长度需在1-50字之间'))
    phone = fields.Str(validate=validate.Length(min=11, max=20, error='手机号长度不正确'))
    gender = fields.Str(allow_none=True, validate=validate.OneOf(['男', '女', '其他'], error='性别只能是男/女/其他'))
    age = fields.Int(allow_none=True, validate=validate.Range(min=0, max=150, error='年龄范围不正确'))
    address = fields.Str(allow_none=True, validate=validate.Length(max=200, error='地址长度不能超过200字'))
    medical_history = fields.Str(allow_none=True, validate=validate.Length(max=1000, error='病史备注长度不能超过1000字'))

    @validates('phone')
    def validate_phone(self, value):
        if value and not re.match(r'^1[3-9]\d{9}$', value):
            raise ValidationError('手机号格式不正确，请输入11位有效手机号')


class PatientQuerySchema(Schema):
    name = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)
    page = fields.Int(allow_none=True, load_default=1, validate=validate.Range(min=1, error='页码必须大于0'))
    page_size = fields.Int(allow_none=True, load_default=20, validate=validate.Range(min=1, max=100, error='每页数量需在1-100之间'))
