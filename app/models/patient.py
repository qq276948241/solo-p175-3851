from datetime import datetime
from app import db


NO_SHOW_THRESHOLD = 3
DEFAULT_CREDIT_SCORE = 100
NO_SHOW_PENALTY = 30
FULFILL_BONUS = 5


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

    def is_blacklisted(self):
        return self.no_show_count >= NO_SHOW_THRESHOLD

    def record_no_show(self):
        self.no_show_count = (self.no_show_count or 0) + 1
        self.credit_score = max(0, (self.credit_score or DEFAULT_CREDIT_SCORE) - NO_SHOW_PENALTY)

    def record_fulfill(self):
        self.credit_score = min(100, (self.credit_score or DEFAULT_CREDIT_SCORE) + FULFILL_BONUS)

    def to_dict(self):
        return {
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
