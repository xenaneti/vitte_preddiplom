from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Enrollment, Lesson, Student, StudyGroup, Teacher


@transaction.atomic
def transfer_student(student, group, date, note):
    student = Student.objects.select_for_update().get(pk=student.pk)
    current = student.enrollments.filter(ended_on__isnull=True).first()
    if not current:
        raise ValidationError("У студента нет действующей записи о группе.")
    if current.group_id == group.pk:
        raise ValidationError("Студент уже обучается в этой группе.")
    if date <= current.started_on:
        raise ValidationError(
            "Дата перевода должна быть позже начала обучения в группе."
        )
    if student.marks.filter(lesson__date__gte=date).exists():
        raise ValidationError(
            "На эту дату или позже уже есть отметки. Выберите дату после последней отметки."
        )
    current.ended_on = date - timedelta(days=1)
    current.save(update_fields=["ended_on"])
    enrollment = Enrollment(student=student, group=group, started_on=date, note=note)
    enrollment.full_clean()
    enrollment.save()
    return enrollment


@transaction.atomic
def withdraw_student(student, date, note):
    student = Student.objects.select_for_update().get(pk=student.pk)
    current = student.enrollments.filter(ended_on__isnull=True).first()
    if not current or not student.is_active:
        raise ValidationError("У студента уже завершено обучение.")
    if date <= current.started_on or date > timezone.localdate():
        raise ValidationError(
            "Укажите дату после начала обучения, не позднее сегодняшнего дня."
        )
    if student.marks.filter(lesson__date__gte=date).exists():
        raise ValidationError(
            "На дату отчисления или позже уже есть отметки. Проверьте дату."
        )
    current.ended_on = date - timedelta(days=1)
    current.end_note = f"Отчисление {date:%d.%m.%Y}: {note}"
    current.save(update_fields=["ended_on", "end_note"])
    student.is_active = False
    student.save(update_fields=["is_active"])


@transaction.atomic
def save_lesson(form):
    lesson = form.save(commit=False)
    Teacher.objects.select_for_update().get(pk=lesson.assignment.teacher_id)
    StudyGroup.objects.select_for_update().get(pk=lesson.assignment.group_id)
    if lesson.pk:
        current = Lesson.objects.select_for_update().get(pk=lesson.pk)
        if current.marks.exists():
            for name in ["assignment_id", "date", "starts_at", "ends_at"]:
                if getattr(current, name) != getattr(lesson, name):
                    raise ValidationError(
                        "У занятия уже есть отметки. Дату, время и назначение менять нельзя."
                    )
        lesson.state = current.state
        lesson.cancellation_reason = current.cancellation_reason
        lesson.cancelled_at = current.cancelled_at
        lesson.cancelled_by = current.cancelled_by
        lesson.closed_at = current.closed_at
        lesson.closed_by = current.closed_by
    lesson.full_clean()
    lesson.save()
    return lesson


@transaction.atomic
def cancel_lesson(user, lesson_id, reason):
    if not user.is_administrator:
        raise PermissionDenied
    lesson = Lesson.objects.select_for_update().get(pk=lesson_id)
    if lesson.state != "planned" or lesson.marks.exists():
        raise ValidationError(
            "Отменить можно только запланированное занятие без отметок."
        )
    if not reason.strip():
        raise ValidationError("Укажите причину отмены.")
    lesson.state = "cancelled"
    lesson.cancellation_reason = reason.strip()
    lesson.cancelled_at = timezone.now()
    lesson.cancelled_by = user
    lesson.full_clean()
    lesson.save(
        update_fields=["state", "cancellation_reason", "cancelled_at", "cancelled_by"]
    )
    return lesson
