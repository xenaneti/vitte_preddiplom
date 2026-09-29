from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from college.access import can_mark, lesson_students, visible_lessons
from college.models import Student
from .models import Attendance, AttendanceChange


def snapshot(mark):
    if not mark:
        return {}
    return {'status': mark.status, 'late_minutes': mark.late_minutes, 'reason_id': mark.reason_id, 'comment': mark.comment}


@transaction.atomic
def save_marks(user, lesson_id, rows, close=False):
    lesson = visible_lessons(user).select_for_update(of=('self',)).get(pk=lesson_id)
    if lesson.state == 'cancelled':
        raise ValidationError('Отменённое занятие нельзя заполнять.')
    if lesson.date > timezone.localdate():
        raise ValidationError('Отметки доступны в день занятия или позже.')
    teacher_access = can_mark(user, lesson)
    if not teacher_access and user.role != 'curator':
        raise PermissionDenied
    student_ids = [student_id for student_id, data in rows]
    list(Student.objects.filter(pk__in=student_ids).order_by('pk').select_for_update())
    allowed_students = set(lesson_students(lesson).values_list('id', flat=True))
    changes = 0
    for student_id, data in rows:
        if student_id not in allowed_students:
            raise ValidationError('Студент не входил в группу на дату занятия.')
        mark = Attendance.objects.select_related('reason').filter(lesson=lesson, student_id=student_id).first()
        if data['version'] != (mark.version if mark else 0):
            raise ValidationError('Журнал уже изменён другим пользователем. Обновите страницу и повторите правку.')
        if not data.get('status'):
            if mark:
                raise ValidationError('Сохранённую отметку нельзя заменить пустой ячейкой.')
            continue
        before = snapshot(mark)
        previous_reason = mark.reason.name if mark and mark.reason else ''
        after = {'status': data['status'], 'late_minutes': data['late_minutes'], 'reason_id': data['reason'].pk if data.get('reason') else None, 'comment': data.get('comment', '')}
        if before == after:
            continue
        explanation = data.get('explanation', '').strip()
        reason = data.get('reason')
        if reason and not reason.is_active and (not mark or mark.reason_id != reason.pk):
            raise ValidationError('Эта причина пропуска больше не используется. Выберите действующую.')
        if not teacher_access:
            if not mark or mark.status not in ('absent', 'excused') or after['status'] not in ('absent', 'excused'):
                raise PermissionDenied('Куратор уточняет только причины пропусков своей группы.')
            if not explanation:
                raise ValidationError('Укажите основание уточнения пропуска.')
        if lesson.state == 'completed' and not explanation:
            raise ValidationError('Для исправления закрытого журнала укажите причину.')
        if after['status'] not in dict(Attendance.STATUSES):
            raise ValidationError('Неизвестная отметка.')
        if not mark:
            mark = Attendance(lesson=lesson, student_id=student_id, updated_by=user)
        else:
            mark.version += 1
        mark.status = after['status']
        mark.late_minutes = after['late_minutes']
        mark.reason_id = after['reason_id']
        mark.comment = after['comment']
        mark.updated_by = user
        mark.full_clean()
        mark.save()
        if before:
            before['reason_name'] = previous_reason
        after['reason_name'] = mark.reason.name if mark.reason else ''
        AttendanceChange.objects.create(attendance=mark, author=user, before=before, after=after, explanation=explanation)
        changes += 1
    if close:
        if not teacher_access:
            raise PermissionDenied
        if not allowed_students:
            raise ValidationError('В группе нет студентов на дату занятия.')
        if lesson.marks.filter(student_id__in=allowed_students).count() != len(allowed_students):
            raise ValidationError('Заполните отметки всех студентов перед закрытием журнала.')
        if lesson.state != 'completed':
            lesson.state = 'completed'
            lesson.closed_at = timezone.now()
            lesson.closed_by = user
            lesson.save(update_fields=['state', 'closed_at', 'closed_by'])
    return changes
