import urllib.request
import os
from datetime import date, timedelta

BASE_URL = 'http://127.0.0.1:8080'
export_dir = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(export_dir, exist_ok=True)

def download_export(path, label):
    try:
        before_count = len(os.listdir(export_dir))
        req = urllib.request.Request(f'{BASE_URL}{path}')
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            from datetime import datetime
            fname = f'{label}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            fpath = os.path.join(export_dir, fname)
            with open(fpath, 'wb') as f:
                f.write(data)
        size_kb = round(os.path.getsize(fpath) / 1024, 1)
        after_count = len(os.listdir(export_dir))
        print(f'  ✅ {label}: {fname} ({size_kb}KB)')
        return True
    except Exception as e:
        print(f'  ❌ {label}: 错误 {e}')
        return False

print('=== Excel 导出功能测试 ===')
print()
print('测试 4 种导出接口:')

tomorrow = date.today() + timedelta(days=1)
while tomorrow.weekday() == 2:
    tomorrow += timedelta(days=1)
date_str = tomorrow.strftime('%Y-%m-%d')

download_export('/api/exports/patients', '患者列表')
download_export(f'/api/exports/appointments?start_date={date_str}&end_date={date_str}', f'预约记录({date_str})')
download_export(f'/api/exports/records?start_date={date_str}&end_date={date_str}', f'诊疗记录({date_str})')
download_export(f'/api/exports/summary?date={date_str}', f'营业日报({date_str})')

print()
print(f'=== 导出目录共 {len(os.listdir(export_dir))} 个Excel文件 ===')
for f in sorted(os.listdir(export_dir)):
    fp = os.path.join(export_dir, f)
    sz = round(os.path.getsize(fp) / 1024, 1)
    print(f'  {f}  ({sz} KB)')

print()
print('=== 服务仍在运行，可在浏览器访问 http://127.0.0.1:8080/ 查看接口列表 ===')
