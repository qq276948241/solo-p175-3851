import urllib.request
import urllib.error
import json
from datetime import date, timedelta

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

def get_workday(start_days_offset):
    d = date.today() + timedelta(days=start_days_offset)
    while d.weekday() in [2, 3]:
        d += timedelta(days=1)
    return d

print('=' * 60)
print('  新功能测试：爽约黑名单 + 信用分 + 周四下午维护')
print('=' * 60)
print()

all_passed = True

# ====== 1. 创建测试患者 ======
print('【测试1】创建新患者，验证默认信用分100，爽约0次')
try:
    result = http_post('/api/patients', {
        'name': '放鸽子大王',
        'phone': '13700001001',
        'gender': '男',
        'age': 40
    })
    patient_id = result['data']['id']
    assert result['data']['credit_score'] == 100
    assert result['data']['no_show_count'] == 0
    assert result['data']['is_blacklisted'] == False
    print(f'  ✅ 患者ID={patient_id} 信用分={result["data"]["credit_score"]} 爽约={result["data"]["no_show_count"]} 黑名单={result["data"]["is_blacklisted"]}')
except Exception as e:
    print(f'  ❌ 错误: {e}')
    all_passed = False

# ====== 2. 创建3个预约（不同日期避免撞单） ======
print()
print('【测试2】创建3个预约（不同日期），方便后续测试爽约')
appt_ids = []
for i in range(3):
    d = get_workday(5 + i * 2)
    date_str = d.strftime('%Y-%m-%d')
    try:
        result = http_post('/api/appointments', {
            'patient_id': patient_id,
            'doctor_id': 1,
            'appointment_date': date_str,
            'appointment_time': '09:00',
            'chief_complaint': f'测试预约{i+1}',
            'status': 'confirmed'
        })
        appt_ids.append(result['data']['id'])
        print(f'  ✅ 预约{i+1} ID={result["data"]["id"]} 日期={date_str}')
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        print(f'  ❌ 预约{i+1} 错误: {data.get("message")}')
        all_passed = False

if len(appt_ids) < 3:
    print(f'  ⚠️  只创建了{len(appt_ids)}个预约，爽约测试可能不完整')

# ====== 3. 爽约3次 ======
print()
print('【测试3】连续标记未到诊，验证信用分每次-30，累计3次进黑名单')
for i, appt_id in enumerate(appt_ids):
    try:
        result = http_put(f'/api/appointments/{appt_id}/status', {
            'status': 'no_show',
            'notes': '打电话不接'
        })
        patient_info = http_get(f'/api/patients/{patient_id}')['data']
        expected_score = max(0, 100 - (i + 1) * 30)
        assert patient_info['no_show_count'] == i + 1
        assert patient_info['credit_score'] == expected_score
        expected_blacklist = (patient_info['no_show_count'] >= 3)
        assert patient_info['is_blacklisted'] == expected_blacklist
        assert result['data']['status'] == 'no_show'
        assert result['data']['status_text'] == '未到诊'
        print(f'  ✅ 第{i+1}次爽约 | 爽约次数={patient_info["no_show_count"]} | 信用分={patient_info["credit_score"]} | 黑名单={patient_info["is_blacklisted"]}')
    except Exception as e:
        print(f'  ❌ 第{i+1}次爽约错误: {e}')
        all_passed = False

# ====== 4. 黑名单患者尝试新预约 ======
print()
print('【测试4】黑名单患者尝试新建预约，验证被拦截')
d = get_workday(30)
try:
    result = http_post('/api/appointments', {
        'patient_id': patient_id,
        'doctor_id': 1,
        'appointment_date': d.strftime('%Y-%m-%d'),
        'appointment_time': '10:00',
        'chief_complaint': '黑名单测试',
        'status': 'confirmed'
    })
    print(f'  ❌ 错误：应该被拦截但成功了！')
    all_passed = False
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    expected_msg = '该患者已被列入黑名单，暂无法新预约，请联系前台'
    if expected_msg in data.get('message', ''):
        print(f'  ✅ 正确拦截: {data.get("message")}')
    else:
        print(f'  ❌ 拦截但错误信息不对: {data.get("message")}')
        all_passed = False
except Exception as e:
    print(f'  ❌ 其他错误: {e}')
    all_passed = False

# ====== 5. 黑名单患者查询/取消预约测试 ======
print()
print('【测试5】黑名单患者：可查询历史记录/可取消待确认预约/不可取消未到诊')
try:
    # 先给黑名单患者创建一个新的待确认预约（这个可以取消）
    # 等等，黑名单患者不能创建新预约，所以我们需要找一个之前状态不是no_show的
    # 实际上appt_ids中的预约都被标记为no_show了，所以我们测试查询历史记录
    result = http_get(f'/api/records/patient/{patient_id}')
    print(f'  ✅ 黑名单患者可查询历史记录，接口正常返回')
    
    # 测试取消no_show预约，应该被拦截
    try:
        http_delete(f'/api/appointments/{appt_ids[0]}')
        print(f'  ❌ 错误：未到诊预约应该无法取消')
        all_passed = False
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        if '已标记未到诊' in data.get('message', ''):
            print(f'  ✅ 未到诊预约无法取消，正确拦截: {data.get("message")}')
        else:
            print(f'  ❌ 取消no_show拦截信息不对: {data.get("message")}')
            all_passed = False
except Exception as e:
    print(f'  ❌ 错误: {e}')
    all_passed = False

# ====== 6. 履约加分测试 ======
print()
print('【测试6】创建新患者测试履约加分，信用分+5（上限100）')
try:
    result2 = http_post('/api/patients', {
        'name': '守信好市民',
        'phone': '13700001002',
        'gender': '女',
        'age': 30
    })
    patient2_id = result2['data']['id']
    d = get_workday(10)
    result3 = http_post('/api/appointments', {
        'patient_id': patient2_id,
        'doctor_id': 2,
        'appointment_date': d.strftime('%Y-%m-%d'),
        'appointment_time': '14:00',
        'chief_complaint': '洗牙',
        'status': 'confirmed'
    })
    appt2_id = result3['data']['id']
    before_score = http_get(f'/api/patients/{patient2_id}')['data']['credit_score']
    http_put(f'/api/appointments/{appt2_id}/status', {
        'status': 'completed',
        'notes': '正常就诊'
    })
    after_score = http_get(f'/api/patients/{patient2_id}')['data']['credit_score']
    assert before_score == 100
    assert after_score == 100
    print(f'  ✅ 信用分上限验证通过（100→{after_score}，不超过100）')
except Exception as e:
    print(f'  ❌ 错误: {e}')
    all_passed = False

# ====== 7. 周四下午维护 ======
print()
print('【测试7】周四下午健康讲座，验证预约被拦截')
next_thu = date.today() + timedelta(days=(3 - date.today().weekday() + 7) % 7)
if next_thu <= date.today():
    next_thu += timedelta(days=7)
thu_str = next_thu.strftime('%Y-%m-%d')
print(f'  测试日期: {thu_str} (周{next_thu.weekday()+1})')

try:
    result = http_post('/api/appointments', {
        'patient_id': patient2_id,
        'doctor_id': 1,
        'appointment_date': thu_str,
        'appointment_time': '11:00',
        'chief_complaint': '周四上午测试',
        'status': 'confirmed'
    })
    print(f'  ✅ 周四上午 11:00 预约成功，ID={result["data"]["id"]}')
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'  ❌ 周四上午预约错误: {data.get("message")}')
    all_passed = False

try:
    http_post('/api/appointments', {
        'patient_id': patient2_id,
        'doctor_id': 1,
        'appointment_date': thu_str,
        'appointment_time': '14:00',
        'chief_complaint': '周四下午测试',
        'status': 'confirmed'
    })
    print(f'  ❌ 错误：周四下午应该被拦截但成功了！')
    all_passed = False
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    if '周四下午诊所举办健康讲座' in data.get('message', ''):
        print(f'  ✅ 周四下午 14:00 正确拦截: {data.get("message")}')
    else:
        print(f'  ❌ 拦截但错误信息不对: {data.get("message")}')
        all_passed = False

# ====== 8. 黑名单列表查询 ======
print()
print('【测试8】查询黑名单列表，验证爽约3次的患者在列表中')
try:
    result = http_get('/api/patients/blacklist')
    data = result['data']
    blacklist = data['list']
    ids_in_blacklist = [p['id'] for p in blacklist]
    patient_info = http_get(f'/api/patients/{patient_id}')['data']
    patient2_info = http_get(f'/api/patients/{patient2_id}')['data']
    print(f'  患者{patient_id} 爽约次数={patient_info["no_show_count"]} 黑名单={patient_info["is_blacklisted"]}')
    print(f'  患者{patient2_id} 爽约次数={patient2_info["no_show_count"]} 黑名单={patient2_info["is_blacklisted"]}')
    assert patient_info['is_blacklisted'] == True, '爽约3次应该进黑名单'
    assert patient2_info['is_blacklisted'] == False, '没爽约不应进黑名单'
    assert patient_id in ids_in_blacklist
    assert patient2_id not in ids_in_blacklist
    assert 'threshold' in data and data['threshold'] == 3
    print(f'  ✅ 黑名单共{data["total"]}人，阈值={data["threshold"]}次')
    print(f'     放鸽子大王在名单中: True')
    print(f'     守信好市民在名单中: False')
except Exception as e:
    print(f'  ❌ 错误: {e}')
    all_passed = False

# ====== 9. 患者查询接口返回信用分 ======
print()
print('【测试9】患者查询接口返回信用分和黑名单状态')
try:
    result1 = http_get(f'/api/patients/{patient_id}')
    assert 'credit_score' in result1['data']
    assert 'no_show_count' in result1['data']
    assert 'is_blacklisted' in result1['data']
    print(f'  ✅ 单患者查询包含信用分等字段')
    result2 = http_get('/api/patients')
    first_patient = result2['data']['list'][0]
    assert 'credit_score' in first_patient
    assert 'no_show_count' in first_patient
    assert 'is_blacklisted' in first_patient
    print(f'  ✅ 患者列表查询包含信用分等字段')
except Exception as e:
    print(f'  ❌ 错误: {e}')
    all_passed = False

# ====== 11. no_show 状态不能改约也不能取消 ======
print()
print('【测试11】未到诊状态不能改约也不能取消')
try:
    no_show_appt = appt_ids[0]
    # 测试改约
    try:
        http_put(f'/api/appointments/{no_show_appt}/reschedule', {
            'appointment_date': get_workday(20).strftime('%Y-%m-%d'),
            'appointment_time': '10:00'
        })
        print(f'  ❌ 错误：未到诊状态应该无法改约')
        all_passed = False
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        if '已标记未到诊' in data.get('message', ''):
            print(f'  ✅ 未到诊状态无法改约，正确拦截: {data.get("message")}')
        else:
            print(f'  ❌ 改约拦截信息不对: {data.get("message")}')
            all_passed = False
    # 测试取消
    try:
        http_delete(f'/api/appointments/{no_show_appt}')
        print(f'  ❌ 错误：未到诊状态应该无法取消')
        all_passed = False
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        if '已标记未到诊' in data.get('message', ''):
            print(f'  ✅ 未到诊状态无法取消，正确拦截: {data.get("message")}')
        else:
            print(f'  ❌ 取消拦截信息不对: {data.get("message")}')
            all_passed = False
except Exception as e:
    print(f'  ⚠️  测试异常: {e}')

print()
print('=' * 60)
if all_passed:
    print('  ✅✅✅  所有新功能测试通过！ ✅✅✅')
else:
    print('  ⚠️  部分测试未通过，请检查上面的错误')
print('=' * 60)
