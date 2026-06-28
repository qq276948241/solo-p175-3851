from datetime import datetime, date, timedelta


BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 18
LUNCH_START_HOUR = 12
LUNCH_END_HOUR = 13
SLOT_MINUTES = 15
CLOSED_WEEKDAY = 2
WEEKEND_PEAK_END_HOUR = 12


def is_business_day(target_date):
    if target_date.weekday() == CLOSED_WEEKDAY:
        return False
    return True


def is_weekend(target_date):
    return target_date.weekday() >= 5


def generate_time_slots(target_date=None, include_weekend_peak=False):
    slots = []
    current_time = datetime(2000, 1, 1, BUSINESS_START_HOUR, 0)
    end_time = datetime(2000, 1, 1, BUSINESS_END_HOUR, 0)
    lunch_start = datetime(2000, 1, 1, LUNCH_START_HOUR, 0)
    lunch_end = datetime(2000, 1, 1, LUNCH_END_HOUR, 0)
    weekend_peak_end = datetime(2000, 1, 1, WEEKEND_PEAK_END_HOUR, 0)

    if target_date and is_weekend(target_date):
        if include_weekend_peak:
            end_time = weekend_peak_end

    while current_time < end_time:
        if not (lunch_start <= current_time < lunch_end):
            slots.append(current_time.strftime('%H:%M'))
        current_time += timedelta(minutes=SLOT_MINUTES)

    return slots


def get_available_slots(doctor_id, target_date, booked_times):
    if not is_business_day(target_date):
        return []

    weekend = is_weekend(target_date)
    all_slots = generate_time_slots(target_date, include_weekend_peak=True)

    if weekend:
        morning_slots = generate_time_slots(target_date, include_weekend_peak=True)
        afternoon_start = datetime(2000, 1, 1, LUNCH_END_HOUR, 0)
        end_time = datetime(2000, 1, 1, BUSINESS_END_HOUR, 0)
        extra_slots = []
        current = afternoon_start
        while current < end_time:
            extra_slots.append(current.strftime('%H:%M'))
            current += timedelta(minutes=SLOT_MINUTES)
        all_slots = morning_slots + extra_slots

    available = []
    for slot in all_slots:
        is_booked = False
        for booked in booked_times:
            if booked == slot:
                is_booked = True
                break
        available.append({
            'time': slot,
            'available': not is_booked
        })

    return available


def validate_time_slot(time_str, target_date):
    slots = generate_time_slots(target_date)
    return time_str in slots


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def get_today():
    return date.today()
