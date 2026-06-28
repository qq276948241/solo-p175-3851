from flask import jsonify
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError


class ApiException(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_error_handlers(app):
    @app.errorhandler(ApiException)
    def handle_api_exception(error):
        response = jsonify({
            'code': error.status_code,
            'message': error.message,
            'data': None
        })
        response.status_code = error.status_code
        return response

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        messages = error.messages
        first_error = ''
        if isinstance(messages, dict):
            for field, errors in messages.items():
                if isinstance(errors, list) and len(errors) > 0:
                    first_error = f'{field}: {errors[0]}'
                    break
        if not first_error:
            first_error = '请求数据格式错误'
        response = jsonify({
            'code': 400,
            'message': first_error,
            'data': None
        })
        response.status_code = 400
        return response

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        msg = str(error.orig)
        if 'UNIQUE' in msg or 'unique' in msg:
            if 'phone' in msg:
                message = '该手机号已存在'
            elif 'unique_doctor_datetime' in msg:
                message = '该医生此时段已被预约'
            elif 'unique_patient_doctor_date' in msg:
                message = '同一患者不能在同一天重复预约同一医生'
            else:
                message = '数据唯一约束冲突'
        else:
            message = '数据操作失败，请稍后重试'
        response = jsonify({
            'code': 400,
            'message': message,
            'data': None
        })
        response.status_code = 400
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        response = jsonify({
            'code': 404,
            'message': '请求的资源不存在',
            'data': None
        })
        response.status_code = 404
        return response

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        response = jsonify({
            'code': 405,
            'message': '请求方法不允许',
            'data': None
        })
        response.status_code = 405
        return response

    @app.errorhandler(500)
    def handle_internal_error(error):
        response = jsonify({
            'code': 500,
            'message': '服务器内部错误，请稍后重试',
            'data': None
        })
        response.status_code = 500
        return response


def success_response(data=None, message='操作成功'):
    return jsonify({
        'code': 200,
        'message': message,
        'data': data
    }), 200
