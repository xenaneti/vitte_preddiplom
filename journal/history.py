from .models import Attendance


def describe_mark(values, reasons):
    if not values:
        return 'Не отмечено'
    text = dict(Attendance.STATUSES).get(values.get('status'), 'Неизвестная отметка')
    if values.get('late_minutes'):
        text += f', {values["late_minutes"]} мин.'
    reason = values.get('reason_name') or reasons.get(values.get('reason_id'), '')
    if reason:
        text += f': {reason}'
    return text


def describe_changes(records, reasons):
    for record in records:
        record.before_text = describe_mark(record.before, reasons)
        record.after_text = describe_mark(record.after, reasons)
