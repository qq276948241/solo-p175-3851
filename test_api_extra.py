import urllib.request
import urllib.error
import json
from datetime import date, timedelta
import os

BASE_URL = 'http://127.0.0.1:8080'

def http_get(path):
    with urllib.request.urlopen(f'{BASE_URL}{path}') as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_post(path, payload):
    req = urllib.request.Request(
        f'{BASE_URL}{path}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_put(path, payload):
    req = urllib.request.Request(
        f'{BASE_URL}{path}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_delete(path):
    req = urllib.request.Request(
        f'{BASE_URL}{path}',
        method='DELETE'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

print('=== 补充测试1: 再创建一个患者 ===')
try:
    result = http_post('/api/patients', {
        'name': '李阿姨',
        'phone': '13888888888',
        'gender': '女',
        'age': 58
    })
    print(f"患者2: ID={result['data']['id']} 姓名={result['data']['name']}")
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'错误: {data.get("message")}')

print()
print('=== 补充测试2: 创建第2个预约(李医生) ===')
tomorrow = date.today() + timedelta(days=1)
while tomorrow.weekday() == 2:
    tomorrow += timedelta(days=1)
date_str = tomorrow.strftime('%Y-%m-%d')
try:
    result = http_post('/api/appointments', {
        'patient_id': 2,
        'doctor_id': 2,
        'appointment_date': date_str,
        'appointment_time': '10:30',
        'chief_complaint': '种植牙复查',
        'status': 'pending'
    })
    appt2_id = result['data']['id']
    print(f"预约2: ID={appt2_id} 时间={result['data']['appointment_date']} {result['data']['appointment_time']} 状态={result['data']['status_text']}")
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'错误: {data.get("message")}')
    appt2_id = None

print()
print('=== 补充测试3: 改约(把预约2改到11:00) ===')
if appt2_id:
    try:
        result = http_put(f'/api/appointments/{appt2_id}/reschedule', {
            'appointment_date': date_str,
            'appointment_time': '11:00',
            'notes': '患者来电改时间'
        })
        print(f"改约成功: 新时间={result['data']['appointment_date']} {result['data']['appointment_time']}")
        print(f"备注包含改约记录: {'改约记录' in (result['data']['notes'] or '')}")
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        print(f'错误: {data.get("message")}')

print()
print('=== 补充测试4: 尝试重复时段撞单验证 ===')
try:
    http_post('/api/appointments', {
        'patient_id': 1,
        'doctor_id': 1,
        'appointment_date': date_str,
        'appointment_time': '09:00',
        'chief_complaint': '撞单测试'
    })
    print('错误：应该被拦截!')
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'正确拦截: {data.get("message")}')

print()
print('=== 补充测试5: 患者就诊历史查询 ===')
try:
    result = http_get('/api/records/patient/1')
    print(f"患者1 就诊次数={result['data']['total_visits']} 累计费用={result['data']['total_fees']}元")
    print(f"第1次就诊: 诊断={result['data']['records'][0]['diagnosis']} 费用={result['data']['records'][0]['fees']}")
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'错误: {data.get("message")}')

print()
print('=== 补充测试6: 当日排班查询 ===')
try:
    result = http_get(f'/api/doctors/schedule?date={date_str}')
    info = result['data']
    print(f"日期={info['date']} 营业={info['is_business_day']} 周末={info['weekend']}")
    for d in info['doctors']:
        print(f"  {d['doctor_name']}: 已约{d['total_booked']}个, 可约{d['total_available']}个")
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'错误: {data.get("message")}')

print()
print('=== 补充测试7: 周三休业验证 ===')
next_wed = date.today() + timedelta(days=(2 - date.today().weekday() + 7) % 7)
if next_wed <= date.today():
    next_wed += timedelta(days=7)
wed_str = next_wed.strftime('%Y-%m-%d')
print(f"测试日期: {wed_str} (周{next_wed.weekday()+1})")
try:
    result = http_get(f'/api/doctors/available-slots?doctor_id=1&date={wed_str}')
    info = result['data']
    print(f"周三营业?={info['is_business_day']} 提示: {info.get('note', '无')}")
    print(f"时段数={len(info['slots'])}")
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'错误: {data.get("message")}')

print()
print('=== 补充测试8: 导出患者Excel ===')
export_dir = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(export_dir, exist_ok=True)
try:
    before = set(os.listdir(export_dir)) if os.path.exists(export_dir) else set()
    req = urllib.request.Request(f'{BASE_URL}/api/exports/patients')
    with urllib.request.urlopen(req) as resp:
        content_disposition = resp.headers.get('Content-Disposition', '')
        filename = None
        if 'filename=' in content_disposition:
            import re
            m = re.search(r'filename="?(.+?)"?$', content_disposition)
            if m:
                filename = m.group(1)
        if not filename:
            filename = f'患者列表_{date.today().strftime("%Y%m%d")}.xlsx'
        filepath = os.path.join(export_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(resp.read())
    size_kb = round(os.path.getsize(filepath) / 1024, 1)
    print(f'患者列表导出成功: {filename} ({size_kb}KB)')
except Exception as e:
    print(f'错误: {e}')

print()
print('=== 补充测试9: 导出预约Excel ===')
try:
    req = urllib.request.Request(f'{BASE_URL}/api/exports/appointments?start_date={date_str}&end_date={date_str}')
    with urllib.request.urlopen(req) as resp:
        content_disposition = resp.headers.get('Content-Disposition', '')
        import re
        m = re.search(r'filename="?(.+?)"?$', content_disposition)
        filename = m.group(1) if m else f'预约记录.xlsx'
        filepath = os.path.join(export_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(resp.read())
    size_kb = round(os.path.getsize(filepath) / 1024, 1)
    print(f'预约记录导出成功: {filename} ({size_kb}KB)')
except Exception as e:
    print(f'错误: {e}')

print()
print('=== 补充测试10: 取消预约 ===')
if appt2_id:
    try:
        result = http_delete(f'/api/appointments/{appt2_id}')
        print(f"预约{appt2_id} 取消后状态: {result['data']['status_text']}")
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        print(f'错误: {data.get("message")}')

print()
print('=== 补充测试11: 更新预约状态 ===')
try:
    result = http_put(f'/api/appointments/1/status', {
        'status': 'completed',
        'notes': '患者按时就诊，已完成治疗'
    })
    print(f"预约1 更新后状态: {result['data']['status_text']}")
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'错误: {data.get("message")}')

print()
print('=== 补充测试12: 手机号格式错误验证 ===')
try:
    http_post('/api/patients', {
        'name': '格式错',
        'phone': '12345',
        'gender': '男'
    })
    print('错误：应该被拦截!')
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'正确拦截: {data.get("message")}')

print()
print('=== 所有补充测试完成 ===')
export_files = os.listdir(export_dir) if os.path.exists(export_dir) else []
print(f'exports目录现有 {len(export_files)} 个Excel文件:')
for f in sorted(export_files):
    fp = os.path.join(export_dir, f)
    sz = round(os.path.getsize(fp) / 1024, 1)
    print(f'  - {f} ({sz}KB)')
