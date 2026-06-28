# 社区牙科诊所预约管理API - 架构说明

> 给接手项目的同事看的接地气版文档，不说空话，直接讲怎么跑起来的。

---

## 一、项目是干啥的

社区牙科诊所，俩医生，患者经常打电话改时间，之前用Excel记老撞单。这个API就是解决这个问题的：

- 患者建档（手机号唯一）
- 按医生+日期查可约时段（15分钟一个号）
- 预约、改约、取消
- 医生写诊疗记录
- 数据导出Excel给前台

后面又加了爽约黑名单、信用分、信用分变动历史这些功能。

---

## 二、技术栈

没啥花里胡哨的，都是Python Web全家桶：

| 技术 | 用途 | 说人话 |
|---|---|---|
| Flask | Web框架 | 接收HTTP请求的 |
| Flask-SQLAlchemy | ORM | 不用写SQL，用Python操作数据库 |
| marshmallow | 参数校验 | 前端传过来的JSON对不对，它先把一道关 |
| SQLite | 数据库 | 小诊所够用，文件型数据库不用装服务 |
| openpyxl | Excel导出 | 生成.xlsx文件 |
| urllib | 测试用 | 测试脚本直接发HTTP请求，不用装requests |

---

## 三、目录结构

```
project175/
├── run.py                    # 入口文件，python run.py 启动
├── requirements.txt          # 依赖包列表
├── app/
│   ├── __init__.py           # Flask应用工厂，create_app()在这里
│   ├── config.py             # 配置（数据库路径这些）
│   ├── models/               # 纯ORM映射，数据库表长啥样
│   │   ├── patient.py        # 患者表 + 信用分历史表
│   │   ├── appointment.py    # 预约表
│   │   ├── doctor.py         # 医生表
│   │   └── medical_record.py # 诊疗记录表
│   ├── schemas/              # 参数校验，marshmallow的Schema
│   │   ├── patient.py
│   │   ├── appointment.py
│   │   ├── doctor.py
│   │   └── medical_record.py
│   ├── services/             # 业务逻辑层，核心规则都在这
│   │   └── appointment_service.py  # 预约相关的所有业务校验
│   ├── utils/                # 工具函数，纯函数无副作用
│   │   ├── business.py       # 时段生成、营业时间判断这些
│   │   ├── errors.py         # 统一异常处理、统一响应格式
│   │   └── init_data.py      # 初始化医生数据
│   └── routes/               # 路由层，只负责接参和返参
│       ├── patients.py
│       ├── appointments.py
│       ├── doctors.py
│       ├── records.py
│       └── exports.py
├── data/                     # SQLite数据库文件存在这
├── exports/                  # 生成的Excel文件存在这
└── test_*.py                 # 测试脚本们
```

**各层职责划重点：**

- **routes（路由层）**：最傻的一层。Flask接收到HTTP请求，它把参数取出来，丢给schemas校验，校验过了调用service，service返回结果它包装成JSON返回。**不做任何业务判断**。

- **schemas（校验层）**：安检口。字段有没有传、格式对不对、长度够不够、枚举值在不在范围内，它说了算。比如预约状态必须是那7个值之一，手机号必须11位。

- **services（业务层）**：最聪明的一层。所有业务规则都在这，比如"黑名单患者不能新预约"、"周三全天不营业"、"周四下午不接新预约"、"同一患者同一天不能约同一个医生"。每个校验失败就抛异常。

- **models（模型层）**：数据库代言人。只定义表结构和基本的to_dict()方法，**不掺业务逻辑**。

- **utils（工具层）**：纯函数集中营。给输入就有输出，不读数据库不改状态。比如"给我一个日期，告诉我是不是周三"、"给我一个日期和医生，返回所有可约时段"。

---

## 四、核心流程剖析

### 4.1 预约创建全流程

前台打电话来说"张大爷要约张医生下周一上午9点看牙"，系统从收到请求到落库，经历了这些：

```
HTTP POST /api/appointments
        ↓
[路由层] routes/appointments.py #L17-L26
  1. 取request.get_json()
  2. 丢给AppointmentCreateSchema.load()校验
        ↓ 校验失败抛ValidationError，被全局异常处理器捕获返回中文错误
[校验层] schemas/appointment.py #L8-L27
  - patient_id 必须 >= 1
  - doctor_id 必须 >= 1
  - appointment_date 格式必须是 YYYY-MM-DD
  - appointment_time 格式必须是 HH:MM
  - status 必须在 VALID_STATUSES 7个值里
        ↓ 校验通过，返回clean过的data字典
[业务层] services/appointment_service.py #L29-L56
  AppointmentService.create_appointment(data) 按顺序跑校验链：
  1. _validate_patient() → 患者存在不？
  2. _validate_patient_not_blacklisted() → 在黑名单不？
  3. _validate_doctor() → 医生存在不？
  4. _validate_date() → 日期格式转成datetime
  5. _validate_business_day() → 周三？不营业！
  6. _validate_not_thursday_afternoon() → 周四下午？做讲座不接！
  7. _validate_time_slot() → 时段在营业时间内不？
  8. _validate_no_duplicate_patient_same_day() → 今天约过这个医生不？
  9. _validate_slot_available() → 这个时段被别人占了不？
        ↓ 任何一步失败抛ApiException("中文错误信息")
  10. 全部通过 → 创建Appointment对象 → db.session.add() → commit()
        ↓
[模型层] models/appointment.py
  定义表结构：id, patient_id, doctor_id, appointment_date, appointment_time, ...
        ↓
[路由层] 拿到appointment对象 → 调to_dict() → success_response()包装返回
        ↓
HTTP 200 {code:200, message:"预约成功", data:{...}}
```

**关键代码片段 - 路由层有多傻：**

```python
# routes/appointments.py #L17-L26
@bp.route('/appointments', methods=['POST'])
def create_appointment():
    schema = AppointmentCreateSchema()
    try:
        data = schema.load(request.get_json() or {})  # 1. 校验参数
    except ValidationError as e:
        raise e

    appointment = AppointmentService.create_appointment(data)  # 2. 全交给service
    return success_response(appointment.to_dict(), '预约成功')  # 3. 返回结果
```

**关键代码片段 - Service层校验链：**

```python
# services/appointment_service.py #L29-L43
@staticmethod
def create_appointment(data):
    patient = AppointmentService._validate_patient(data['patient_id'])
    AppointmentService._validate_patient_not_blacklisted(patient)
    doctor = AppointmentService._validate_doctor(data['doctor_id'])
    target_date = AppointmentService._validate_date(data['appointment_date'])
    AppointmentService._validate_business_day(target_date)
    AppointmentService._validate_not_thursday_afternoon(target_date, data['appointment_time'])
    AppointmentService._validate_time_slot(data['appointment_time'], target_date)
    AppointmentService._validate_no_duplicate_patient_same_day(patient.id, doctor.id, target_date)
    AppointmentService._validate_slot_available(doctor.id, target_date, data['appointment_time'])
    # ... 9个校验全过才落库
```

### 4.2 改约流程

改约和创建预约走**同一个Service类**，复用大部分校验逻辑：

```
HTTP PUT /api/appointments/<id>/reschedule
        ↓
[路由层] routes/appointments.py #L77-L86
  1. 取参数 → AppointmentRescheduleSchema 校验
  2. 调用 AppointmentService.reschedule_appointment(id, data)
        ↓
[业务层] services/appointment_service.py #L58-L87
  1. get_appointment_or_404() → 预约存在不？
  2. _validate_can_reschedule() → 已经是"未到诊"、"已取消"、"医生改约"这种终态？不给改！
  3. 复用创建时的校验：日期、营业日、时段、撞单检查
     （注意：撞单检查会排除当前这个预约ID，不然自己跟自己撞）
  4. 黑名单检查也要重新跑（改约时患者可能刚被拉黑）
  5. 更新时间 + 备注里追加改约记录
  6. commit()
```

**状态分类是个重点**，最近刚修的bug：

```python
# services/appointment_service.py #L12-L24
FULFILL_STATUSES = {'completed'}                     # 履约 → +5分
NO_SHOW_STATUSES = {'no_show'}                       # 爽约 → -30分
NEUTRAL_STATUSES = {'pending', 'confirmed',          # 中性 → 不动分数
                    'cancelled', 'doctor_reschedule', 'patient_cancel'}
```

只有**跨类转换**才触发信用调整，中性状态之间怎么改都不碰分数。这样"医生改约"就不会冤枉好人了。

### 4.3 异常怎么串起来的

三层各抛各的异常，最后在 [utils/errors.py](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo175/project175/app/utils/errors.py) 统一处理：

- **schemas层**抛 `ValidationError` → 全局处理器抓了，提取第一个错误信息返回
- **services层**抛 `ApiException("该患者已被列入黑名单...")` → 处理器直接返回这个中文信息
- **数据库层**抛 `IntegrityError` → 处理器判断是UNIQUE约束，返回"该手机号已存在"之类
- 统一返回格式：`{code: xxx, message: "中文错误", data: null}`

---

## 五、测试策略

项目根目录有5个测试文件，全是用Python自带的`urllib`发HTTP请求，不需要装额外依赖。

### 5.1 测试文件分工

| 测试文件 | 覆盖场景 | 什么时候跑 |
|---|---|---|
| **test_api.py** | 核心功能7项：根路径、医生列表、患者建档、时段查询、预约创建、手机号查重、诊疗记录 | 改了核心逻辑必跑 |
| **test_api_extra.py** | 边缘场景12项：改约、撞单、就诊历史、当日排班、周三休业、取消预约、状态更新、格式校验 | 改了业务规则必跑 |
| **test_exports.py** | 4种Excel导出：患者、预约、诊疗记录、营业日报 | 改了导出逻辑必跑 |
| **test_new_features.py** | 新功能11项：黑名单、信用分、周四维护、履约上限、列表查询 | 新功能开发完跑 |
| **test_status_classification.py** | 状态分类验证10个场景：医生改约不扣分、患者取消不扣分、信用分历史完整 | 改了状态机逻辑必跑 |

### 5.2 urllib怎么连本地8080

测试脚本不依赖第三方库，用Python标准库`urllib.request`：

```python
# test_api.py #L1-L16
import urllib.request
import urllib.error
import json

BASE_URL = 'http://127.0.0.1:8080'

# GET请求
with urllib.request.urlopen(f'{BASE_URL}/api/doctors') as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print(f'状态码: {resp.status}')

# POST请求
req = urllib.request.Request(
    f'{BASE_URL}/api/patients',
    data=json.dumps(patient_data).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

# 捕获错误返回
try:
    with urllib.request.urlopen(req) as resp:
        ...
except urllib.error.HTTPError as e:
    data = json.loads(e.read().decode('utf-8'))
    print(f'HTTP错误: {e.code} - {data.get("message")}')
```

### 5.3 新功能开发完的回归顺序

按"从核心到边缘"的顺序跑，前面挂了后面就不用看了：

1. **先跑 test_api.py** → 核心功能别跪
2. **再跑 test_api_extra.py** → 边缘场景别崩
3. **再跑 test_exports.py** → 导出别坏
4. **再跑 test_new_features.py** → 新功能正常
5. **最后跑你自己加的专项测试**（比如 test_status_classification.py）

> 💡 跑测试之前记得先 `python run.py` 启动服务，端口8080。测试会往数据库里写数据，跑完可以删掉 `data/clinic.db` 重置。

---

## 六、改代码的时候注意啥

1. **业务规则只往 service 里加**，别往路由层塞
2. **新增状态记得同步三处**：models的get_status_text()、schemas的VALID_STATUSES、services的状态分类集合
3. **状态变更要考虑防重复触发**：比如 `completed → no_show → completed` 别扣两次分加两次分
4. **改约和创建走同一套校验**，改了创建的校验记得看改约要不要同步
5. **异常信息全写中文**，前台看得懂

---

看完这篇应该对整个项目脉络清楚了，剩下的就是对着代码细节啃了。有问题直接翻对应文件的代码，每层职责划得挺清的，不会乱。
