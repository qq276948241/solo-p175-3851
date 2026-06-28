from app import create_app

app = create_app()


@app.route('/')
def index():
    from app.utils.errors import success_response
    data = {
        'name': '社区牙科诊所预约管理API',
        'version': '1.0.0',
        'description': '提供患者建档、预约管理、诊疗记录、Excel导出等功能',
        'business_hours': {
            'workdays': '周一、周二、周四、周五',
            'weekend': '周六、周日（上午高峰）',
            'closed': '周三全天休息',
            'morning': '9:00 - 12:00',
            'afternoon': '13:00 - 18:00',
            'slot_duration': '15分钟/号'
        },
        'endpoints': {
            '患者管理': [
                'POST /api/patients - 患者建档',
                'GET /api/patients - 患者列表查询',
                'GET /api/patients/<id> - 查询单个患者',
                'GET /api/patients/phone/<phone> - 手机号查患者',
                'PUT /api/patients/<id> - 更新患者信息',
                'DELETE /api/patients/<id> - 删除患者'
            ],
            '医生管理': [
                'POST /api/doctors - 新增医生',
                'GET /api/doctors - 医生列表',
                'GET /api/doctors/<id> - 查询单个医生',
                'GET /api/doctors/available-slots?doctor_id=&date= - 查可约时段',
                'GET /api/doctors/schedule?date= - 当日全部排班'
            ],
            '预约管理': [
                'POST /api/appointments - 创建预约',
                'GET /api/appointments - 预约列表',
                'GET /api/appointments/<id> - 查询单个预约',
                'PUT /api/appointments/<id> - 更新预约备注',
                'PUT /api/appointments/<id>/reschedule - 改约',
                'PUT /api/appointments/<id>/status - 更新状态',
                'DELETE /api/appointments/<id> - 取消预约'
            ],
            '诊疗记录': [
                'POST /api/records - 写诊疗记录',
                'GET /api/records - 记录列表',
                'GET /api/records/<id> - 查询单条记录',
                'GET /api/records/patient/<patient_id> - 患者就诊历史',
                'PUT /api/records/<id> - 更新记录',
                'DELETE /api/records/<id> - 删除记录'
            ],
            'Excel导出': [
                'GET /api/exports/patients - 导出患者列表',
                'GET /api/exports/appointments?start_date=&end_date= - 导出预约',
                'GET /api/exports/records?start_date=&end_date= - 导出诊疗记录',
                'GET /api/exports/summary?date= - 导出每日营业日报'
            ]
        }
    }
    return success_response(data, '欢迎使用牙科诊所预约管理API')


if __name__ == '__main__':
    print('=' * 60)
    print('  社区牙科诊所预约管理系统 API')
    print('  服务地址: http://127.0.0.1:8080')
    print('  接口文档: http://127.0.0.1:8080/')
    print('=' * 60)
    app.run(host='0.0.0.0', port=8080, debug=False)
