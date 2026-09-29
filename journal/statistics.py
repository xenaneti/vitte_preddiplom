from django.db.models import Count, Q

from college.access import visible_lessons
from .models import Attendance


def totals(records):
    result = records.aggregate(
        total=Count("id"),
        present=Count("id", filter=Q(status="present")),
        absent=Count("id", filter=Q(status="absent")),
        late=Count("id", filter=Q(status="late")),
        excused=Count("id", filter=Q(status="excused")),
    )
    result["percentage"] = (
        round(100 * (result["present"] + result["late"]) / result["total"], 1)
        if result["total"]
        else None
    )
    return result


def report_data(user, form):
    lessons = form.filter_lessons(visible_lessons(user))
    marks = Attendance.objects.filter(lesson__in=lessons.filter(state="completed"))
    if form.is_valid() and form.cleaned_data.get("student"):
        marks = marks.filter(student=form.cleaned_data["student"])
    groups = (
        marks.values("lesson__assignment__group__code")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status="present")),
            late=Count("id", filter=Q(status="late")),
            absent=Count("id", filter=Q(status="absent")),
            excused=Count("id", filter=Q(status="excused")),
        )
        .order_by("lesson__assignment__group__code")
    )
    rows = []
    for group in groups:
        group["name"] = group["lesson__assignment__group__code"]
        group["percentage"] = round(
            100 * (group["present"] + group["late"]) / group["total"], 1
        )
        rows.append(group)
    return {
        "marks": marks,
        "totals": totals(marks),
        "groups": rows,
        "unfinished": lessons.filter(state="planned").count(),
    }


def detailed_statistics(marks):
    counts = {
        "total": Count("id"),
        "present": Count("id", filter=Q(status="present")),
        "late": Count("id", filter=Q(status="late")),
        "absent": Count("id", filter=Q(status="absent")),
        "excused": Count("id", filter=Q(status="excused")),
    }
    students = list(
        marks.values(
            "student_id",
            "student__number",
            "student__last_name",
            "student__first_name",
            "student__middle_name",
        )
        .annotate(**counts)
        .order_by("student__last_name", "student__first_name", "student_id")
    )
    disciplines = list(
        marks.values(
            "lesson__assignment__discipline_id",
            "lesson__assignment__discipline__code",
            "lesson__assignment__discipline__name",
        )
        .annotate(**counts)
        .order_by(
            "lesson__assignment__discipline__name",
            "lesson__assignment__discipline__code",
        )
    )
    days = list(
        marks.values("lesson__date").annotate(**counts).order_by("lesson__date")
    )
    for row in students:
        row["name"] = " ".join(
            filter(
                None,
                [
                    row["student__last_name"],
                    row["student__first_name"],
                    row["student__middle_name"],
                ],
            )
        )
    for row in disciplines:
        row["name"] = (
            f'{row["lesson__assignment__discipline__name"]} '
            f'({row["lesson__assignment__discipline__code"]})'
        )
    for row in students + disciplines + days:
        row["percentage"] = round(
            100 * (row["present"] + row["late"]) / row["total"], 1
        )
    return {"student_rows": students, "discipline_rows": disciplines, "day_rows": days}
