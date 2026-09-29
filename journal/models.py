from django.conf import settings
from django.db import models
from django.db.models import Q

from college.models import Lesson, Student


class AbsenceReason(models.Model):
    code = models.SlugField("Код", max_length=25, unique=True)
    name = models.CharField("Причина", max_length=100)
    description = models.CharField("Пояснение", max_length=250)
    needs_confirmation = models.BooleanField("Нужно подтверждение", default=True)
    is_active = models.BooleanField("Используется", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "причина пропуска"
        verbose_name_plural = "причины пропусков"

    def __str__(self):
        return self.name


class Attendance(models.Model):
    STATUSES = [
        ("present", "Присутствовал"),
        ("absent", "Отсутствовал"),
        ("late", "Опоздал"),
        ("excused", "Уважительная причина"),
    ]
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name="marks")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="marks")
    status = models.CharField("Отметка", max_length=10, choices=STATUSES)
    late_minutes = models.PositiveSmallIntegerField("Минут опоздания", default=0)
    reason = models.ForeignKey(
        AbsenceReason,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Причина пропуска",
    )
    comment = models.CharField("Комментарий", max_length=300, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "student"], name="unique_lesson_student"
            ),
            models.CheckConstraint(
                condition=Q(version__gte=1), name="attendance_version_positive"
            ),
            models.CheckConstraint(
                condition=Q(status__in=["present", "absent", "late", "excused"]),
                name="attendance_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="late", late_minutes__gte=1, late_minutes__lte=180)
                    | (~Q(status="late") & Q(late_minutes=0))
                ),
                name="attendance_minutes_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="excused", reason__isnull=False)
                    | (~Q(status="excused") & Q(reason__isnull=True))
                ),
                name="attendance_reason_valid",
            ),
        ]
        indexes = [models.Index(fields=["student", "status"])]

    def __str__(self):
        return f"{self.student}: {self.get_status_display()}"


class AttendanceChange(models.Model):
    attendance = models.ForeignKey(
        Attendance, on_delete=models.PROTECT, related_name="changes"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    before = models.JSONField("Было", default=dict)
    after = models.JSONField("Стало")
    explanation = models.CharField("Основание изменения", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["created_at"])]
