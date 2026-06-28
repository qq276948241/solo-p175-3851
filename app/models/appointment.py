from datetime import datetime
from app import db


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, comment='患者ID')
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, comment='医生ID')
    appointment_date = db.Column(db.Date, nullable=False, index=True, comment='预约日期')
    appointment_time = db.Column(db.String(10), nullable=False, comment='预约时段(HH:MM)')
    status = db.Column(db.String(20), default='pending', comment='状态:pending-待确认 confirmed-已确认 completed-已完成 cancelled-已取消')
    chief_complaint = db.Column(db.String(200), comment='主诉')
    notes = db.Column(db.String(500), comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    medical_records = db.relationship('MedicalRecord', backref='appointment', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'appointment_date', 'appointment_time', name='unique_doctor_datetime'),
        db.UniqueConstraint('patient_id', 'doctor_id', 'appointment_date', name='unique_patient_doctor_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.name if self.patient else None,
            'patient_phone': self.patient.phone if self.patient else None,
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor.name if self.doctor else None,
            'appointment_date': self.appointment_date.strftime('%Y-%m-%d'),
            'appointment_time': self.appointment_time,
            'status': self.status,
            'status_text': self.get_status_text(),
            'chief_complaint': self.chief_complaint,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    def get_status_text(self):
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'completed': '已完成',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, '未知')
