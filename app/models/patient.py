from datetime import datetime
from app import db


NO_SHOW_THRESHOLD = 3
DEFAULT_CREDIT_SCORE = 100
NO_SHOW_PENALTY = 30
FULFILL_BONUS = 5


class CreditScoreLog(db.Model):
    __tablename__ = 'credit_score_logs'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True, comment='患者ID')
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True, comment='关联预约ID')
    change_type = db.Column(db.String(20), nullable=False, comment='变动类型:bonus-加分 penalty-扣分 init-初始化')
    change_amount = db.Column(db.Integer, nullable=False, comment='变动分值(正数加分，负数扣分)')
    score_before = db.Column(db.Integer, nullable=False, comment='变动前信用分')
    score_after = db.Column(db.Integer, nullable=False, comment='变动后信用分')
    no_show_count_before = db.Column(db.Integer, nullable=True, comment='变动前爽约次数')
    no_show_count_after = db.Column(db.Integer, nullable=True, comment='变动后爽约次数')
    reason = db.Column(db.String(200), comment='变动原因')
    operator = db.Column(db.String(50), comment='操作人')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'appointment_id': self.appointment_id,
            'change_type': self.change_type,
            'change_type_text': '加分' if self.change_type == 'bonus' else ('扣分' if self.change_type == 'penalty' else '初始化'),
            'change_amount': self.change_amount,
            'score_before': self.score_before,
            'score_after': self.score_after,
            'no_show_count_before': self.no_show_count_before,
            'no_show_count_after': self.no_show_count_after,
            'reason': self.reason,
            'operator': self.operator,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, comment='患者姓名')
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True, comment='手机号(唯一标识)')
    gender = db.Column(db.String(10), comment='性别')
    age = db.Column(db.Integer, comment='年龄')
    address = db.Column(db.String(200), comment='住址')
    medical_history = db.Column(db.Text, comment='病史备注')
    credit_score = db.Column(db.Integer, default=DEFAULT_CREDIT_SCORE, comment='信用分，默认100')
    no_show_count = db.Column(db.Integer, default=0, comment='爽约次数')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    appointments = db.relationship('Appointment', backref='patient', lazy=True, cascade='all, delete-orphan')
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy=True, cascade='all, delete-orphan')
    credit_score_logs = db.relationship('CreditScoreLog', backref='patient', lazy=True, cascade='all, delete-orphan')

    def is_blacklisted(self):
        return (self.no_show_count or 0) >= NO_SHOW_THRESHOLD

    def record_no_show(self, appointment_id=None, reason=None):
        score_before = self.credit_score or DEFAULT_CREDIT_SCORE
        no_show_before = self.no_show_count or 0

        self.no_show_count = no_show_before + 1
        self.credit_score = max(0, score_before - NO_SHOW_PENALTY)

        log = CreditScoreLog(
            patient_id=self.id,
            appointment_id=appointment_id,
            change_type='penalty',
            change_amount=-NO_SHOW_PENALTY,
            score_before=score_before,
            score_after=self.credit_score,
            no_show_count_before=no_show_before,
            no_show_count_after=self.no_show_count,
            reason=reason or '患者未到诊，爽约记录'
        )
        db.session.add(log)

    def record_fulfill(self, appointment_id=None, reason=None):
        score_before = self.credit_score or DEFAULT_CREDIT_SCORE
        no_show_before = self.no_show_count or 0

        self.credit_score = min(100, score_before + FULFILL_BONUS)

        log = CreditScoreLog(
            patient_id=self.id,
            appointment_id=appointment_id,
            change_type='bonus',
            change_amount=FULFILL_BONUS,
            score_before=score_before,
            score_after=self.credit_score,
            no_show_count_before=no_show_before,
            no_show_count_after=no_show_before,
            reason=reason or '患者按时到诊，正常履约'
        )
        db.session.add(log)

    def get_credit_score_logs(self, page=1, page_size=20):
        query = CreditScoreLog.query.filter_by(patient_id=self.id).order_by(CreditScoreLog.created_at.desc())
        total = query.count()
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'list': [log.to_dict() for log in pagination.items]
        }

    def to_dict(self, include_logs=False):
        result = {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'gender': self.gender,
            'age': self.age,
            'address': self.address,
            'medical_history': self.medical_history,
            'credit_score': self.credit_score,
            'no_show_count': self.no_show_count,
            'is_blacklisted': self.is_blacklisted(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
        if include_logs:
            result['credit_score_logs'] = self.get_credit_score_logs()
        return result
