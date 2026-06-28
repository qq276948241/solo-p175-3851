import urllib.request
import urllib.error
import json
from datetime import date, timedelta

BASE_URL = 'http://127.0.0.1:8080'

print('=== 测试1: 获取根路径 ===')
try:
    with urllib.request.urlopen(f'{BASE_URL}/') as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f'状态码: {resp.status}')
        print(f'消息: {data.get("message")}')
        print(f'API名称: {data.get("data",{}).get("name")}')
except Exception as e:
    print(f'错误: {e}')

print()
print('=== 测试2: 获取医生列表 ===')
try:
    with urllib.request.urlopen(f'{BASE_URL}/api/doctors') as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f'状态码: {resp.status}')
        print(f'消息: {data.get("message")}')
        doctors = data.get('data', [])
        for d in doctors:
            print(f'  医生ID:{d["id"]} 姓名:{d["name"]} 专长:{d["specialty"]}')
except Exception as e:
    print(f'错误: {e}')

print()
print('=== 测试3: 创建患者 ===')
patient_id = None
try:
    patient_data = {
        'name': '测试患者',
        'phone': '13912345678',
        'gender': '男',
        'age': 35,
        'address': '测试地址1号',
        'medical_history': '无特殊病史'
    }
    req = urllib.request.Request(
        f'{BASE_URL}/api/patients',
        data=json.dumps(patient_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f'状态码: {resp.status}')
        print(f'消息: {data.get("message")}')
        patient_id = data.get('data', {}).get('id')
        print(f'患者ID: {patient_id}')
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'HTTP错误: {e.code} - {data.get("message")}')
    msg = data.get('message', '')
    if '已存在' in msg or '已注册' in msg:
        try:
            with urllib.request.urlopen(f'{BASE_URL}/api/patients/phone/13912345678') as resp2:
                data2 = json.loads(resp2.read().decode('utf-8'))
                patient_id = data2.get('data', {}).get('id')
                print(f'已存在患者ID: {patient_id}')
        except Exception as e2:
            print(f'查询已有患者错误: {e2}')
except Exception as e:
    print(f'错误: {e}')

print()
print('=== 测试4: 查询可约时段 ===')
tomorrow = date.today() + timedelta(days=1)
while tomorrow.weekday() == 2:
    tomorrow += timedelta(days=1)
date_str = tomorrow.strftime('%Y-%m-%d')
print(f'查询日期: {date_str}')
available = []
try:
    with urllib.request.urlopen(f'{BASE_URL}/api/doctors/available-slots?doctor_id=1&date={date_str}') as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f'消息: {data.get("message")}')
        info = data.get('data', {})
        print(f'医生: {info.get("doctor_name")}')
        print(f'是否营业日: {info.get("is_business_day")}')
        slots = info.get('slots', [])
        available = [s for s in slots if s['available']]
        print(f'可用时段数: {len(available)} / 总时段数: {len(slots)}')
        if available:
            print(f'第一个可用时段: {available[0]["time"]}')
except Exception as e:
    print(f'错误: {e}')

print()
print('=== 测试5: 创建预约 ===')
appt_id = None
if patient_id and available:
    slot_time = available[0]['time']
    try:
        appt_data = {
            'patient_id': patient_id,
            'doctor_id': 1,
            'appointment_date': date_str,
            'appointment_time': slot_time,
            'chief_complaint': '牙痛检查',
            'status': 'confirmed'
        }
        req = urllib.request.Request(
            f'{BASE_URL}/api/appointments',
            data=json.dumps(appt_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f'消息: {data.get("message")}')
            appt = data.get('data', {})
            appt_id = appt.get('id')
            print(f'预约ID: {appt_id}')
            print(f'预约时间: {appt.get("appointment_date")} {appt.get("appointment_time")}')
            print(f'状态: {appt.get("status_text")}')
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        print(f'HTTP错误: {e.code} - {data.get("message")}')
    except Exception as e:
        print(f'错误: {e}')
else:
    print(f'跳过：patient_id={patient_id}, 可用时段数={len(available)}')

print()
print('=== 测试6: 手机号重复建档验证 ===')
try:
    dup_data = {
        'name': '测试重复',
        'phone': '13912345678',
        'gender': '女'
    }
    req = urllib.request.Request(
        f'{BASE_URL}/api/patients',
        data=json.dumps(dup_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        print(f'错误：未拦截重复手机号！')
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'正确拦截: {data.get("message")}')
except Exception as e:
    print(f'错误: {e}')

print()
print('=== 测试7: 写诊疗记录 ===')
if patient_id and appt_id:
    try:
        record_data = {
            'patient_id': patient_id,
            'doctor_id': 1,
            'appointment_id': appt_id,
            'diagnosis': '轻度龋齿',
            'treatment': '树脂充填治疗',
            'prescription': '布洛芬缓释胶囊 0.3g bid*3天',
            'fees': 380.00,
            'notes': '建议三个月后复查'
        }
        req = urllib.request.Request(
            f'{BASE_URL}/api/records',
            data=json.dumps(record_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f'消息: {data.get("message")}')
            record = data.get('data', {})
            print(f'记录ID: {record.get("id")}')
            print(f'诊断: {record.get("diagnosis")}')
            print(f'费用: {record.get("fees")}元')
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        print(f'HTTP错误: {e.code} - {data.get("message")}')
    except Exception as e:
        print(f'错误: {e}')
else:
    print('跳过：患者或预约不存在')

print()
print('=== 所有核心功能测试完成 ===')
