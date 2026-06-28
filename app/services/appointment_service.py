from app import db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.utils.errors import ApiException
from app.utils.business import (
    is_business_day, validate_time_slot, parse_date,
    is_thursday_afternoon, get_available_slots, is_weekend
)


FULFILL_STATUSES = {'completed'}
NO_SHOW_STATUSES = {'no_show'}
NEUTRAL_STATUSES = {'pending', 'confirmed', 'cancelled', 'doctor_reschedule', 'patient_cancel'}

STATUS_TEXT_MAP = {
    'pending': '待确认',
    'confirmed': '已确认',
    'completed': '已完成',
    'cancelled': '已取消',
    'no_show': '未到诊',
    'doctor_reschedule': '医生改约',
    'patient_cancel': '患者取消'
}


class AppointmentService:

    @staticmethod
    def create_appointment(data):
        patient = AppointmentService._validate_patient(data['patient_id'])
        AppointmentService._validate_patient_not_blacklisted(patient)
        doctor = AppointmentService._validate_doctor(data['doctor_id'])
        target_date = AppointmentService._validate_date(data['appointment_date'])
        AppointmentService._validate_business_day(target_date)
        AppointmentService._validate_not_thursday_afternoon(target_date, data['appointment_time'])
        AppointmentService._validate_time_slot(data['appointment_time'], target_date)
        AppointmentService._validate_no_duplicate_patient_same_day(
            patient.id, doctor.id, target_date
        )
        AppointmentService._validate_slot_available(
            doctor.id, target_date, data['appointment_time']
        )

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=target_date,
            appointment_time=data['appointment_time'],
            chief_complaint=data.get('chief_complaint'),
            notes=data.get('notes'),
            status=data.get('status', 'pending')
        )
        db.session.add(appointment)
        db.session.commit()
        return appointment

    @staticmethod
    def reschedule_appointment(appointment_id, data):
        appointment = AppointmentService.get_appointment_or_404(appointment_id)
        AppointmentService._validate_can_reschedule(appointment)

        target_date = AppointmentService._validate_date(data['appointment_date'])
        AppointmentService._validate_business_day(target_date)
        AppointmentService._validate_time_slot(data['appointment_time'], target_date)
        AppointmentService._validate_slot_available(
            appointment.doctor_id, target_date, data['appointment_time'],
            exclude_appointment_id=appointment_id
        )
        AppointmentService._validate_no_duplicate_patient_same_day(
            appointment.patient_id, appointment.doctor_id, target_date,
            exclude_appointment_id=appointment_id
        )

        patient = Patient.query.get(appointment.patient_id)
        if patient:
            AppointmentService._validate_patient_not_blacklisted(patient)

        old_info = f'原预约：{appointment.appointment_date.strftime("%Y-%m-%d")} {appointment.appointment_time}'
        appointment.appointment_date = target_date
        appointment.appointment_time = data['appointment_time']
        if data.get('notes'):
            appointment.notes = (appointment.notes + '\n' if appointment.notes else '') + data['notes']
        appointment.notes = (appointment.notes + '\n' if appointment.notes else '') + f'[改约记录] {old_info} → {data["appointment_date"]} {data["appointment_time"]}'

        db.session.commit()
        return appointment

    @staticmethod
    def update_appointment_status(appointment_id, data):
        appointment = AppointmentService.get_appointment_or_404(appointment_id)

        old_status = appointment.status
        new_status = data['status']

        if old_status != new_status:
            patient = Patient.query.get(appointment.patient_id)
            if patient:
                if new_status in NO_SHOW_STATUSES:
                    if old_status not in NO_SHOW_STATUSES:
                        patient.record_no_show(
                            appointment_id=appointment_id,
                            reason=f'预约状态由「{STATUS_TEXT_MAP.get(old_status, old_status)}」变更为「{STATUS_TEXT_MAP.get(new_status, new_status)}」，记为爽约'
                        )
                elif new_status in FULFILL_STATUSES:
                    if old_status not in NO_SHOW_STATUSES and old_status not in FULFILL_STATUSES:
                        patient.record_fulfill(
                            appointment_id=appointment_id,
                            reason=f'预约状态由「{STATUS_TEXT_MAP.get(old_status, old_status)}」变更为「{STATUS_TEXT_MAP.get(new_status, new_status)}」，正常履约'
                        )

        appointment.status = new_status
        if data.get('notes'):
            status_text = STATUS_TEXT_MAP.get(data['status'], data['status'])
            appointment.notes = (appointment.notes + '\n' if appointment.notes else '') + f'[状态变更] {status_text}：{data["notes"]}'

        db.session.commit()
        return appointment

    @staticmethod
    def cancel_appointment(appointment_id):
        appointment = AppointmentService.get_appointment_or_404(appointment_id)
        AppointmentService._validate_can_cancel(appointment)

        appointment.status = 'cancelled'
        db.session.commit()
        return appointment

    @staticmethod
    def update_appointment_info(appointment_id, data):
        appointment = AppointmentService.get_appointment_or_404(appointment_id)

        if 'chief_complaint' in data:
            if len(data['chief_complaint'] or '') > 200:
                raise ApiException('主诉长度不能超过200字', 400)
            appointment.chief_complaint = data['chief_complaint']
        if 'notes' in data:
            if len(data['notes'] or '') > 500:
                raise ApiException('备注长度不能超过500字', 400)
            appointment.notes = data['notes']

        db.session.commit()
        return appointment

    @staticmethod
    def get_available_slots(doctor_id, date_str):
        if not doctor_id:
            raise ApiException('请指定医生', 400)
        if not date_str:
            raise ApiException('请指定日期', 400)

        target_date = parse_date(date_str)
        if not target_date:
            raise ApiException('日期格式不正确', 400)

        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            raise ApiException('医生不存在', 404)

        booked = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == target_date,
            Appointment.status.in_(['pending', 'confirmed'])
        ).with_entities(Appointment.appointment_time).all()
        booked_times = [b[0] for b in booked]

        slots = get_available_slots(doctor_id, target_date, booked_times)

        return {
            'doctor': doctor.to_dict(),
            'date': date_str,
            'is_business_day': is_business_day(target_date),
            'is_weekend': is_weekend(target_date),
            'available_count': len([s for s in slots if s['available']]),
            'total_count': len(slots),
            'slots': slots
        }

    @staticmethod
    def _validate_patient(patient_id):
        patient = Patient.query.get(patient_id)
        if not patient:
            raise ApiException('患者不存在', 404)
        return patient

    @staticmethod
    def _validate_patient_not_blacklisted(patient):
        if patient.is_blacklisted():
            raise ApiException('该患者已被列入黑名单，暂无法新预约，请联系前台', 400)

    @staticmethod
    def _validate_doctor(doctor_id):
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            raise ApiException('医生不存在', 404)
        if not doctor.is_active:
            raise ApiException('该医生已停诊，无法预约', 400)
        return doctor

    @staticmethod
    def _validate_date(date_str):
        target_date = parse_date(date_str)
        if not target_date:
            raise ApiException('日期格式不正确', 400)
        return target_date

    @staticmethod
    def _validate_business_day(target_date):
        if not is_business_day(target_date):
            raise ApiException('周三全天休息，请选择其他日期', 400)

    @staticmethod
    def _validate_not_thursday_afternoon(target_date, time_str):
        if is_thursday_afternoon(target_date, time_str):
            raise ApiException('周四下午诊所举办健康讲座，暂停新预约，请选择上午或其他日期', 400)

    @staticmethod
    def _validate_time_slot(time_str, target_date):
        if not validate_time_slot(time_str, target_date):
            raise ApiException('预约时段不在营业时间范围内，营业时间：9:00-12:00，13:00-18:00', 400)

    @staticmethod
    def _validate_no_duplicate_patient_same_day(patient_id, doctor_id, target_date, exclude_appointment_id=None):
        query = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == target_date,
            Appointment.status.in_(['pending', 'confirmed', 'completed'])
        )
        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)
        existing = query.first()
        if existing:
            raise ApiException('同一患者不能在同一天重复预约同一医生', 400)

    @staticmethod
    def _validate_slot_available(doctor_id, target_date, time_str, exclude_appointment_id=None):
        query = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == target_date,
            Appointment.appointment_time == time_str,
            Appointment.status.in_(['pending', 'confirmed'])
        )
        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)
        existing = query.first()
        if existing:
            raise ApiException('该时段已被预约，请选择其他时间', 400)

    @staticmethod
    def get_appointment_or_404(appointment_id):
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            raise ApiException('预约不存在', 404)
        return appointment

    @staticmethod
    def _validate_can_reschedule(appointment):
        if appointment.status in FULFILL_STATUSES:
            raise ApiException('已完成的预约无法改约', 400)
        if appointment.status in NO_SHOW_STATUSES:
            raise ApiException('已标记未到诊的预约无法改约', 400)
        if appointment.status in {'cancelled', 'doctor_reschedule', 'patient_cancel'}:
            raise ApiException(f'预约状态为「{STATUS_TEXT_MAP.get(appointment.status)}」，无法改约', 400)

    @staticmethod
    def _validate_can_cancel(appointment):
        if appointment.status in FULFILL_STATUSES:
            raise ApiException('已完成的预约无法取消', 400)
        if appointment.status in NO_SHOW_STATUSES:
            raise ApiException('已标记未到诊的预约无法取消', 400)
        if appointment.status == 'cancelled':
            raise ApiException('预约已取消，无需重复操作', 400)
        if appointment.status in {'doctor_reschedule', 'patient_cancel'}:
            raise ApiException(f'预约状态为「{STATUS_TEXT_MAP.get(appointment.status)}」，无需重复取消', 400)
