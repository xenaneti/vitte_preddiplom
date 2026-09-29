from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from college.access import visible_lessons
from college.models import Enrollment
from .filters import JournalFilter
from .models import Attendance

SYMBOLS = {"present": "П", "absent": "Н", "late": "О", "excused": "У"}


class MatrixFilter(JournalFilter):
    def __init__(self, data, user):
        values = data.copy()
        values.setdefault(
            "date_from", (timezone.localdate() - timedelta(days=6)).isoformat()
        )
        super().__init__(values, user)
        self.fields["group"].required = True
        self.fields["group"].empty_label = "Выберите группу"

    def clean(self):
        data = super().clean()
        start, end = data.get("date_from"), data.get("date_to")
        if start and end and (end - start).days > 30:
            raise forms.ValidationError("Для общего журнала выберите не больше 31 дня.")
        return data


def group_matrix(user, form):
    if not form.is_valid():
        return {"columns": [], "rows": []}
    values = form.cleaned_data
    lessons = (
        form.filter_lessons(visible_lessons(user))
        .exclude(state="cancelled")
        .order_by("date", "starts_at", "id")
    )
    if lessons.count() > 100:
        raise ValidationError(
            "За этот период больше 100 занятий. Сократите период или выберите дисциплину."
        )
    lessons = list(lessons)
    memberships = Enrollment.objects.filter(
        group=values["group"], started_on__lte=values["date_to"]
    )
    memberships = memberships.filter(
        Q(ended_on__isnull=True) | Q(ended_on__gte=values["date_from"])
    ).select_related("student")
    if values.get("student"):
        memberships = memberships.filter(student=values["student"])
    if memberships.count() > 300:
        raise ValidationError(
            "В выборке слишком много студентов. Выберите студента или сократите период."
        )
    students = {}
    periods = {}
    for membership in memberships:
        student_id = membership.student_id
        students[student_id] = membership.student
        periods.setdefault(student_id, []).append(
            (membership.started_on, membership.ended_on)
        )
    marks = Attendance.objects.filter(lesson__in=lessons, student_id__in=students)
    saved = {(mark.student_id, mark.lesson_id): mark for mark in marks}
    rows = []
    for student in sorted(
        students.values(), key=lambda item: (item.last_name, item.first_name, item.pk)
    ):
        row = {"student": student, "cells": [], "total": 0, "attended": 0}
        for lesson in lessons:
            member = any(
                start <= lesson.date and (end is None or lesson.date <= end)
                for start, end in periods[student.pk]
            )
            mark = saved.get((student.pk, lesson.pk))
            cell = {
                "lesson_id": lesson.pk,
                "symbol": "·" if member else "—",
                "status": "",
                "title": "Нет отметки" if member else "Не входил в группу",
            }
            if member and mark:
                cell.update(
                    symbol=SYMBOLS[mark.status],
                    status=mark.status,
                    title=mark.get_status_display(),
                )
                if lesson.state == "completed":
                    row["total"] += 1
                    row["attended"] += mark.status in ("present", "late")
            row["cells"].append(cell)
        row["percentage"] = (
            round(100 * row["attended"] / row["total"], 1) if row["total"] else None
        )
        rows.append(row)
    return {"columns": lessons, "rows": rows}
