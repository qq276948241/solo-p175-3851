from app.models import Doctor
from app import db


def init_doctors():
    existing = Doctor.query.count()
    if existing == 0:
        doctors = [
            Doctor(name='张医生', phone='13800000001', specialty='口腔内科、牙周治疗', is_active=True),
            Doctor(name='李医生', phone='13800000002', specialty='口腔修复、正畸、种植', is_active=True),
        ]
        db.session.add_all(doctors)
        db.session.commit()
