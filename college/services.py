from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Enrollment, Student


@transaction.atomic
def transfer_student(student, group, date, note):
    student = Student.objects.select_for_update().get(pk=student.pk)
    current = student.enrollments.filter(ended_on__isnull=True).first()
    if not current:
        raise ValidationError('У студента нет действующей записи о группе.')
    if current.group_id == group.pk:
        raise ValidationError('Студент уже обучается в этой группе.')
    if date <= current.started_on:
        raise ValidationError('Дата перевода должна быть позже начала обучения в группе.')
    if student.marks.filter(lesson__date__gte=date).exists():
        raise ValidationError('На эту дату или позже уже есть отметки. Выберите дату после последней отметки.')
    current.ended_on = date - timedelta(days=1)
    current.save(update_fields=['ended_on'])
    enrollment = Enrollment(student=student, group=group, started_on=date, note=note)
    enrollment.full_clean()
    enrollment.save()
    return enrollment
