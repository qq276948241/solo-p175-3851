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

def get_workday(start_days_offset):
    d = date.today() + timedelta(days=start_days_offset)
    while d.weekday() in [2, 3]:
        d += timedelta(days=1)
    return d

print('=' * 70)
print('  状态分类 + 信用分历史记录 修复验证')
print('  模拟场景：老患者张大爷（有1次真实爽约）')
print('=' * 70)
print()

all_passed = True

# ====== 1. 创建老患者 ======
print('【场景1】创建老患者「张大爷」')
result = http_post('/api/patients', {
    'name': '张大爷',
    'phone': '13900000666',
    'gender': '男',
    'age': 68
})
patient_id = result['data']['id']
print(f'  ✅ 创建成功 | ID={patient_id} | 信用分={result["data"]["credit_score"]} | 爽约={result["data"]["no_show_count"]} | 黑名单={result["data"]["is_blacklisted"]}')

# ====== 2. 模拟三个月前的一次真实爽约 ======
print()
print('【场景2】模拟三个月前：一次真实爽约（no_show）')
d = get_workday(-30)
appt1 = http_post('/api/appointments', {
    'patient_id': patient_id,
    'doctor_id': 1,
    'appointment_date': d.strftime('%Y-%m-%d'),
    'appointment_time': '14:00',
    'chief_complaint': '三个月前拔牙',
    'status': 'confirmed'
})
before = http_get(f'/api/patients/{patient_id}')['data']
http_put(f'/api/appointments/{appt1["data"]["id"]}/status', {
    'status': 'no_show',
    'notes': '打电话不接，上门没人'
})
after = http_get(f'/api/patients/{patient_id}')['data']
assert after['credit_score'] == 70, f'应该70分，实际{after["credit_score"]}'
assert after['no_show_count'] == 1, f'爽约应该1次，实际{after["no_show_count"]}'
assert after['is_blacklisted'] == False, '1次爽约不应进黑名单'
print(f'  ✅ 真实爽约后 | 信用分 {before["credit_score"]}→{after["credit_score"]} | 爽约次数 {before["no_show_count"]}→{after["no_show_count"]} | 黑名单=False')

# ====== 3. 这次预约：医生临时有事改约 ======
print()
print('【场景3】这次预约：周二下午，医生临时有事，前台手动改为「医生改约」')
d2 = get_workday(2)
appt2 = http_post('/api/appointments', {
    'patient_id': patient_id,
    'doctor_id': 1,
    'appointment_date': d2.strftime('%Y-%m-%d'),
    'appointment_time': '14:00',
    'chief_complaint': '补牙复诊',
    'status': 'confirmed'
})
before2 = http_get(f'/api/patients/{patient_id}')['data']
print(f'  改约前状态 | 信用分={before2["credit_score"]} | 爽约={before2["no_show_count"]}')

result3 = http_put(f'/api/appointments/{appt2["data"]["id"]}/status', {
    'status': 'doctor_reschedule',
    'notes': '张医生临时开会，已电话通知患者改约'
})
after2 = http_get(f'/api/patients/{patient_id}')['data']
print(f'  改为状态: doctor_reschedule = 「{result3["data"]["status_text"]}」')

# ===== 关键验证：中性状态不应该动信用分 ======
assert after2['credit_score'] == before2['credit_score'], f'医生改约不应扣分！信用分 {before2["credit_score"]}→{after2["credit_score"]}'
assert after2['no_show_count'] == before2['no_show_count'], f'医生改约不应加爽约次数！爽约 {before2["no_show_count"]}→{after2["no_show_count"]}'
assert after2['is_blacklisted'] == False, f'医生改约不应进黑名单！信用分={after2["credit_score"]}，爽约={after2["no_show_count"]}'
print(f'  ✅ 医生改约后 | 信用分 {before2["credit_score"]}→{after2["credit_score"]}（不变） | 爽约 {before2["no_show_count"]}→{after2["no_show_count"]}（不变） | 黑名单=False')

# ====== 4. 查询信用分历史，前台能看到为什么进/没进黑名单 ======
print()
print('【场景4】查询信用分变动历史（前台排错用）')
logs = http_get(f'/api/patients/{patient_id}/credit-logs')['data']
print(f'  当前信用分: {logs["current_credit_score"]}')
print(f'  爽约次数: {logs["no_show_count"]}')
print(f'  黑名单状态: {logs["is_blacklisted"]}')
print(f'  变动记录共 {logs["total"]} 条:')
for log in logs['list']:
    print(f'    - {log["created_at"]} | {log["change_type_text"]:>2} {log["change_amount"]:>+3}分 | {log["score_before"]}→{log["score_after"]} | {log["reason"]}')

# 关键验证：只有1条真实扣分记录，没有因为医生改约产生错误扣分
assert logs['total'] == 1, f'应该只有1条变动记录（真实爽约），实际{logs["total"]}条'
assert logs['list'][0]['change_type'] == 'penalty', '唯一一条记录应该是扣分（爽约）'
assert logs['list'][0]['appointment_id'] == appt1['data']['id'], '扣分应该关联到三个月前那次爽约'
print(f'  ✅ 只有1条变动记录（真实爽约扣分），医生改约未产生错误记录')

# ====== 5. 张大爷能不能正常改约？ ======
print()
print('【场景5】张大爷改约到周五下午（关键验证：不应被黑名单拦截）')
new_d = get_workday(5)
try:
    reschedule_result = http_put(f'/api/appointments/{appt2["data"]["id"]}/reschedule', {
        'appointment_date': new_d.strftime('%Y-%m-%d'),
        'appointment_time': '15:00'
    })
    print(f'  ❌ 等等，预约状态是doctor_reschedule，按照规则不应该能改约')
    all_passed = False
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    # 预期：doctor_reschedule是终态，无法改约，应该先改为confirmed再改约
    if '医生改约' in data.get('message', ''):
        print(f'  ✅ doctor_reschedule是终态，正确拦截：{data["message"]}')
        print(f'  说明：前台应该先把 doctor_reschedule 改回 confirmed，再执行改约')
    else:
        print(f'  ⚠️  拦截信息: {data.get("message")}（可能是其他原因）')

# 先改回confirmed，再改约
print()
print('【场景5续】正确流程：先改回confirmed状态，再执行改约')
http_put(f'/api/appointments/{appt2["data"]["id"]}/status', {
    'status': 'confirmed',
    'notes': '重新安排改约'
})
before3 = http_get(f'/api/patients/{patient_id}')['data']
assert before3['credit_score'] == 70, f'改状态回confirmed也不应动分数，实际{before3["credit_score"]}'
assert before3['is_blacklisted'] == False, '不应在黑名单中'
print(f'  ✅ 改回confirmed后 | 信用分={before3["credit_score"]}（不变） | 黑名单={before3["is_blacklisted"]}')

reschedule_result = http_put(f'/api/appointments/{appt2["data"]["id"]}/reschedule', {
    'appointment_date': new_d.strftime('%Y-%m-%d'),
    'appointment_time': '15:00'
})
after3 = http_get(f'/api/patients/{patient_id}')['data']
assert after3['is_blacklisted'] == False, f'改约不应被黑名单拦截！当前信用分={after3["credit_score"]}，爽约={after3["no_show_count"]}'
print(f'  ✅ 改约成功！新时间={reschedule_result["data"]["appointment_date"]} {reschedule_result["data"]["appointment_time"]}')
print(f'     信用分={after3["credit_score"]} | 爽约={after3["no_show_count"]} | 黑名单={after3["is_blacklisted"]}')
print(f'     🎉 张大爷没有被冤枉，能正常改约到周五下午了！')

# ====== 6. 其他中性状态也验证 ======
print()
print('【场景6】验证其他中性状态：患者取消(patient_cancel)')
d3 = get_workday(8)
appt3 = http_post('/api/appointments', {
    'patient_id': patient_id,
    'doctor_id': 2,
    'appointment_date': d3.strftime('%Y-%m-%d'),
    'appointment_time': '10:00',
    'chief_complaint': '洗牙',
    'status': 'confirmed'
})
before4 = http_get(f'/api/patients/{patient_id}')['data']
http_put(f'/api/appointments/{appt3["data"]["id"]}/status', {
    'status': 'patient_cancel',
    'notes': '患者家中有事，提前电话取消'
})
after4 = http_get(f'/api/patients/{patient_id}')['data']
assert after4['credit_score'] == before4['credit_score'], f'患者取消不应扣分！{before4["credit_score"]}→{after4["credit_score"]}'
assert after4['no_show_count'] == before4['no_show_count'], f'患者取消不应加爽约次数！'
print(f'  ✅ 患者取消(patient_cancel) | 信用分{before4["credit_score"]}→{after4["credit_score"]}（不变） | 爽约次数不变')

# ====== 7. 履约状态加分验证 ======
print()
print('【场景7】履约(completed)正常加分')
d4 = get_workday(10)
appt4 = http_post('/api/appointments', {
    'patient_id': patient_id,
    'doctor_id': 1,
    'appointment_date': d4.strftime('%Y-%m-%d'),
    'appointment_time': '09:30',
    'chief_complaint': '补牙',
    'status': 'confirmed'
})
before5 = http_get(f'/api/patients/{patient_id}')['data']
http_put(f'/api/appointments/{appt4["data"]["id"]}/status', {
    'status': 'completed',
    'notes': '补牙完成'
})
after5 = http_get(f'/api/patients/{patient_id}')['data']
assert after5['credit_score'] == before5['credit_score'] + 5, f'履约应该+5分！{before5["credit_score"]}→{after5["credit_score"]}'
print(f'  ✅ 履约(completed) | 信用分{before5["credit_score"]}→{after5["credit_score"]}（+5）')

# ====== 8. 爽约再验证 ======
print()
print('【场景8】再一次真实爽约(no_show)，验证爽约计数正确+历史记录完整')
d5 = get_workday(12)
appt5 = http_post('/api/appointments', {
    'patient_id': patient_id,
    'doctor_id': 2,
    'appointment_date': d5.strftime('%Y-%m-%d'),
    'appointment_time': '11:00',
    'chief_complaint': '复查',
    'status': 'confirmed'
})
before6 = http_get(f'/api/patients/{patient_id}')['data']
http_put(f'/api/appointments/{appt5["data"]["id"]}/status', {
    'status': 'no_show',
    'notes': '联系不上'
})
after6 = http_get(f'/api/patients/{patient_id}')['data']
assert after6['credit_score'] == max(0, before6['credit_score'] - 30), f'爽约应该-30分！{before6["credit_score"]}→{after6["credit_score"]}'
assert after6['no_show_count'] == before6['no_show_count'] + 1, f'爽约次数应该+1'
print(f'  ✅ 第2次爽约(no_show) | 信用分{before6["credit_score"]}→{after6["credit_score"]}（-30）| 爽约次数{before6["no_show_count"]}→{after6["no_show_count"]}')

# ====== 9. 最终信用分历史核对 ======
print()
print('【场景9】最终核对：完整的信用分历史')
final_logs = http_get(f'/api/patients/{patient_id}/credit-logs')['data']
print(f'  患者当前状态 | 信用分={final_logs["current_credit_score"]} | 爽约次数={final_logs["no_show_count"]} | 黑名单={final_logs["is_blacklisted"]}')
print(f'  共 {final_logs["total"]} 条变动记录:')
for i, log in enumerate(final_logs['list']):
    print(f'    [{i+1}] {log["created_at"]} | {log["change_type_text"]:>2} {log["change_amount"]:>+3}分 | {log["score_before"]:>3}→{log["score_after"]:<3} | 爽约{log["no_show_count_before"]}→{log["no_show_count_after"]} | {log["reason"]}')

# 验证历史记录数量正确：1次爽约 + 1次履约 + 1次爽约 = 3条
# 再加1次：1次爽约（三个月前） + 1次履约（补牙完成） + 1次爽约（复查没来） = 共3条
assert final_logs['total'] == 3, f'应该有3条历史记录，实际{final_logs["total"]}条'
penalty_count = sum(1 for l in final_logs['list'] if l['change_type'] == 'penalty')
bonus_count = sum(1 for l in final_logs['list'] if l['change_type'] == 'bonus')
assert penalty_count == 2, f'应该2条扣分记录，实际{penalty_count}条'
assert bonus_count == 1, f'应该1条加分记录，实际{bonus_count}条'
print(f'  ✅ 历史记录完整：2次扣分（爽约）+ 1次加分（履约）= 共3条，无错误记录')

# ====== 10. 再次测试：新状态值doctor_reschedule和patient_cancel能通过schema校验 ======
print()
print('【场景10】验证新状态值可以正常使用（schema已更新）')
d6 = get_workday(15)
appt6 = http_post('/api/appointments', {
    'patient_id': patient_id,
    'doctor_id': 1,
    'appointment_date': d6.strftime('%Y-%m-%d'),
    'appointment_time': '14:30',
    'chief_complaint': '装牙冠',
    'status': 'confirmed'
})
# 测试patient_cancel
r1 = http_put(f'/api/appointments/{appt6["data"]["id"]}/status', {
    'status': 'patient_cancel'
})
assert r1['data']['status'] == 'patient_cancel'
assert r1['data']['status_text'] == '患者取消'
print(f'  ✅ patient_cancel 状态可用 | status_text =「{r1["data"]["status_text"]}」')

appt7 = http_post('/api/appointments', {
    'patient_id': patient_id,
    'doctor_id': 2,
    'appointment_date': get_workday(17).strftime('%Y-%m-%d'),
    'appointment_time': '16:00',
    'chief_complaint': '咨询',
    'status': 'confirmed'
})
# 测试doctor_reschedule
r2 = http_put(f'/api/appointments/{appt7["data"]["id"]}/status', {
    'status': 'doctor_reschedule'
})
assert r2['data']['status'] == 'doctor_reschedule'
assert r2['data']['status_text'] == '医生改约'
print(f'  ✅ doctor_reschedule 状态可用 | status_text =「{r2["data"]["status_text"]}」')

print()
print('=' * 70)
if all_passed:
    print('  ✅✅✅  所有场景验证通过！老患者不再被冤枉进黑名单！ ✅✅✅')
else:
    print('  ⚠️  部分场景未通过，请检查上方输出')
print('=' * 70)
