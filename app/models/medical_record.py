from datetime import datetime
from app import db


class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True, comment='患者ID')
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, comment='医生ID')
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), comment='关联预约ID')
    visit_date = db.Column(db.Date, default=datetime.now().date, nullable=False, comment='就诊日期')
    diagnosis = db.Column(db.Text, comment='诊断')
    treatment = db.Column(db.Text, comment='治疗方案')
    prescription = db.Column(db.Text, comment='处方')
    fees = db.Column(db.Numeric(10, 2), default=0, comment='费用')
    notes = db.Column(db.Text, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    doctor = db.relationship('Doctor', backref='medical_records')

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.name if self.patient else None,
            'patient_phone': self.patient.phone if self.patient else None,
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor.name if self.doctor else None,
            'appointment_id': self.appointment_id,
            'visit_date': self.visit_date.strftime('%Y-%m-%d') if self.visit_date else None,
            'diagnosis': self.diagnosis,
            'treatment': self.treatment,
            'prescription': self.prescription,
            'fees': float(self.fees) if self.fees else 0,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
