# 社区牙科诊所预约管理 API

专为社区小型牙科诊所设计的预约管理后端系统，解决 Excel 记单撞单、改约频繁、排班混乱等痛点。

---

## 一、快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python run.py
```

启动后访问 <http://127.0.0.1:8080/> 可查看完整接口目录和营业时间说明。

> 默认端口 `8080`，如需修改请编辑 `run.py` 最后一行的 `port` 参数。

---

## 二、营业时间规则

| 项目 | 规则 |
|---|---|
| **工作日** | 周一、周二、周四、周五（周三全天休息）|
| **周末** | 周六、周日（上午 9-12 点高峰，下午照常营业）|
| **上午时段** | 09:00 - 12:00 |
| **午休时间** | 12:00 - 13:00（不排号）|
| **下午时段** | 13:00 - 18:00 |
| **每号时长** | 15 分钟 |
| **单日容量** | 每位医生 32 个号（全天约 30+ 个下午号）|

系统内置 **2 位医生**（张医生、李医生），首次启动自动写入数据库。

---

## 三、核心功能

### 3.1 患者建档 / 管理

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/patients` | 新建患者档案（手机号唯一）|
| `GET` | `/api/patients` | 患者列表（支持姓名/手机号模糊搜索，分页）|
| `GET` | `/api/patients/<id>` | 查询单个患者 |
| `GET` | `/api/patients/phone/<phone>` | 用手机号快速查患者 |
| `PUT` | `/api/patients/<id>` | 修改患者信息 |
| `DELETE` | `/api/patients/<id>` | 删除患者（有预约记录时禁止删除）|

**字段说明：**

```json
{
  "name": "王小明",
  "phone": "13912345678",
  "gender": "男",
  "age": 32,
  "address": "XX小区3号楼501",
  "medical_history": "青霉素过敏、高血压"
}
```

- **手机号**：11 位中国大陆手机号格式校验，作为唯一标识，**重复建档自动拦截**。
- 所有错误返回中文提示。

### 3.2 医生 / 排班查询

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/doctors` | 所有医生列表（`?active_only=true` 只查在职）|
| `GET` | `/api/doctors/<id>` | 单个医生信息 |
| `GET` | `/api/doctors/available-slots?doctor_id=1&date=2026-07-02` | 查指定医生指定日期的可约时段 |
| `GET` | `/api/doctors/schedule?date=2026-07-02` | 当日所有医生总览（已约 + 可约 + 预约明细）|

**可约时段返回示例：**

```json
{
  "date": "2026-07-02",
  "doctor_name": "张医生",
  "is_business_day": true,
  "weekend": false,
  "slots": [
    {"time": "09:00", "available": true},
    {"time": "09:15", "available": false},
    {"time": "09:30", "available": true}
  ],
  "total_available": 30,
  "total_booked": 2
}
```

**周三自动返回空时段**并提示"周三全天休息"。

### 3.3 预约管理

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/appointments` | 创建预约 |
| `GET` | `/api/appointments` | 预约列表（按患者/医生/日期范围/状态筛选，分页）|
| `GET` | `/api/appointments/<id>` | 单个预约详情 |
| `PUT` | `/api/appointments/<id>` | 修改主诉/备注 |
| `PUT` | `/api/appointments/<id>/reschedule` | **改约**（改日期/时段，自动写入改约日志）|
| `PUT` | `/api/appointments/<id>/status` | 更新状态（待确认→已确认→已完成 / 取消）|
| `DELETE` | `/api/appointments/<id>` | 取消预约（逻辑删除，状态置为「已取消」）|

**创建预约请求示例：**

```json
{
  "patient_id": 1,
  "doctor_id": 1,
  "appointment_date": "2026-07-02",
  "appointment_time": "14:30",
  "chief_complaint": "右上后牙疼痛3天",
  "status": "confirmed"
}
```

**防撞单规则（全部生效）：**

1. 同一医生 + 同一日期 + 同一时段 → 重复拦截
2. 同一患者 + 同一医生 + 同一日期 → 重复拦截
3. 时段必须在营业范围内（午休排除）
4. 周三不可预约

**改约接口**会自动在备注中追加 `[改约记录] 原时间 → 新时间`，方便前台追溯。

**状态枚举：**

| 值 | 中文 | 说明 |
|---|---|---|
| `pending` | 待确认 | 新建默认值，电话未确认 |
| `confirmed` | 已确认 | 已和患者确认 |
| `completed` | 已完成 | 就诊结束 |
| `cancelled` | 已取消 | 患者/诊所取消 |

### 3.4 诊疗记录（医生写病例）

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/records` | 写诊疗记录（关联预约后自动把预约状态置为已完成）|
| `GET` | `/api/records` | 记录列表（按患者/医生/日期筛选，分页）|
| `GET` | `/api/records/<id>` | 单条记录详情 |
| `GET` | `/api/records/patient/<patient_id>` | **患者就诊全历史**（含就诊次数、累计费用）|
| `PUT` | `/api/records/<id>` | 修改记录 |
| `DELETE` | `/api/records/<id>` | 删除记录 |

**写记录请求示例：**

```json
{
  "patient_id": 1,
  "doctor_id": 1,
  "appointment_id": 1,
  "diagnosis": "右上6 慢性牙髓炎",
  "treatment": "根管治疗RCT，术后建议冠修复",
  "prescription": "阿莫西林胶囊 0.5g tid×3天；布洛芬 0.3g prn",
  "fees": 1280.00,
  "notes": "一周后复诊，避免用患侧咀嚼"
}
```

### 3.5 Excel 导出（前台打印/存档用）

所有导出接口直接返回 `.xlsx` 文件，浏览器访问即可下载。

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/exports/patients` | **患者列表**（全部患者）|
| `GET` | `/api/exports/appointments?start_date=2026-07-01&end_date=2026-07-31` | **预约记录**（按日期范围、医生、患者筛选）|
| `GET` | `/api/exports/records?start_date=&end_date=&doctor_id=1` | **诊疗记录**（按日期、医生筛选，含费用合计行）|
| `GET` | `/api/exports/summary?date=2026-07-02` | **当日营业日报**（所有医生的预约、费用汇总）|

**Excel 特点：**
- 表头蓝色加粗居中，单元格全部边框
- 周末行淡黄色背景高亮
- 费用合计红色加粗显示
- 文件名含时间戳，避免覆盖

导出文件保存到服务器 `exports/` 目录，前台直接用浏览器下载也可以。

---

## 四、统一响应格式

所有接口（包括错误）都返回 **JSON + HTTP 状态码**：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... }
}
```

### 常见中文错误示例

| 场景 | 返回 message |
|---|---|
| 手机号已注册 | `"该手机号已注册，请直接使用"` |
| 重复时段预约 | `"该时段已被预约，请选择其他时间"` |
| 同患者同医生同日重复约 | `"同一患者不能在同一天重复预约同一医生"` |
| 周三预约 | `"周三全天休息，请选择其他日期"` |
| 时段非法 | `"预约时段不在营业时间范围内，营业时间：9:00-12:00，13:00-18:00"` |
| 手机号格式错 | `"phone: 手机号格式不正确，请输入11位有效手机号"` |
| 资源不存在 | `"请求的资源不存在"` / `"患者不存在"` / `"预约不存在"` |

---

## 五、项目结构

```
project175/
├── run.py                  # 启动入口（python run.py）
├── requirements.txt        # 依赖清单
├── data/
│   └── clinic.db           # SQLite 数据库（首次启动自动创建）
├── exports/                # Excel 导出文件存放目录
└── app/
    ├── __init__.py         # Flask 应用工厂 + 蓝图注册
    ├── config.py           # 数据库路径等配置
    ├── models/             # 数据模型层
    │   ├── patient.py          # 患者表
    │   ├── doctor.py           # 医生表
    │   ├── appointment.py      # 预约表（含联合唯一约束防撞单）
    │   └── medical_record.py   # 诊疗记录表
    ├── schemas/            # marshmallow 参数校验层
    │   ├── patient.py
    │   ├── doctor.py
    │   ├── appointment.py
    │   └── medical_record.py
    ├── routes/             # 路由（API 视图层）
    │   ├── patients.py
    │   ├── doctors.py
    │   ├── appointments.py
    │   ├── records.py
    │   └── exports.py
    └── utils/              # 工具类
        ├── business.py         # 营业规则、时段生成
        ├── errors.py           # 全局错误处理器、中文错误
        └── init_data.py        # 首次启动初始化2位医生
```

---

## 六、技术栈

| 技术 | 用途 | 版本 |
|---|---|---|
| **Flask 3.x** | 轻量级 Web 框架 | 3.0+ |
| **Flask-SQLAlchemy 3.x** | ORM 数据库操作 | 3.1+ |
| **SQLAlchemy 2.x** | 数据库引擎（SQLite 文件库）| 2.0.36+ |
| **marshmallow 3.x** | 请求参数校验、中文错误 | 3.20+ |
| **openpyxl 3.x** | Excel 生成（带样式）| 3.1+ |
| **SQLite** | 零配置本地数据库 | Python 内置 |

> 选型理由：**小诊所不需要 MySQL/PostgreSQL**，SQLite 文件库备份方便（直接拷走 `clinic.db` 即可），日常百级数据量完全够用。

---

## 七、测试脚本（可选）

项目自带 3 个测试脚本，启动服务后可直接运行：

```bash
python test_api.py        # 核心功能：建患者、预约、改约、撞单、写病例
python test_api_extra.py  # 扩展：改约日志、休业、取消、状态流转
python test_exports.py    # 4 种 Excel 导出功能测试
```

---

## 八、典型使用流程（前台）

1. **新患者来电** → `POST /api/patients` 建档，记下返回的 `patient_id`
2. **查询可约号** → `GET /api/doctors/available-slots` 看张/李医生哪天有空
3. **帮患者约上** → `POST /api/appointments` 创建预约
4. **患者来电改时间** → `PUT /api/appointments/<id>/reschedule` 改约
5. **医生看完诊** → `POST /api/records` 写入诊断、治疗、费用
6. **下班前导报表** → `GET /api/exports/summary?date=今天` 打印日报
7. **月末导明细** → `GET /api/exports/appointments` 或 `records` 按月导出给会计

---

## 九、数据备份

直接复制 `data/clinic.db` 文件即可完成全量备份（患者、预约、病例、费用全部包含），建议每周复制一份加日期后缀。
