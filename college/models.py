from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Specialty(models.Model):
    code = models.CharField("Код", max_length=20, unique=True)
    name = models.CharField("Название", max_length=180)
    qualification = models.CharField("Квалификация", max_length=120)
    duration = models.PositiveSmallIntegerField("Срок обучения, месяцев", default=46)
    is_active = models.BooleanField("Действует", default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "специальность"
        verbose_name_plural = "специальности"

    def __str__(self):
        return f"{self.code} — {self.name}"


class StudyGroup(models.Model):
    code = models.CharField("Группа", max_length=30, unique=True)
    name = models.CharField("Наименование", max_length=150)
    specialty = models.ForeignKey(
        Specialty, on_delete=models.PROTECT, verbose_name="Специальность"
    )
    admission_year = models.PositiveSmallIntegerField("Год набора")
    graduation_year = models.PositiveSmallIntegerField("Год выпуска")
    study_form = models.CharField(
        "Форма обучения",
        max_length=20,
        choices=[("full", "Очная"), ("part", "Очно-заочная")],
        default="full",
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="curated_groups",
        verbose_name="Куратор",
        limit_choices_to={"role": "curator"},
    )
    is_active = models.BooleanField("Действует", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "группа"
        verbose_name_plural = "группы"
        constraints = [
            models.CheckConstraint(
                condition=Q(graduation_year__gt=F("admission_year")),
                name="group_years_order",
            )
        ]

    def clean(self):
        if self.curator_id and self.curator.role != "curator":
            raise ValidationError(
                {"curator": "Выберите пользователя с ролью куратора."}
            )

    def __str__(self):
        return self.code


class Student(models.Model):
    number = models.CharField("Номер студента", max_length=25, unique=True)
    last_name = models.CharField("Фамилия", max_length=100)
    first_name = models.CharField("Имя", max_length=100)
    middle_name = models.CharField("Отчество", max_length=100, blank=True)
    birth_date = models.DateField("Дата рождения")
    email = models.EmailField("Почта", blank=True)
    admitted_at = models.DateField("Дата зачисления")
    is_active = models.BooleanField("Обучается", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name", "id"]
        verbose_name = "студент"
        verbose_name_plural = "студенты"
        constraints = [
            models.CheckConstraint(
                condition=Q(birth_date__lt=F("admitted_at")),
                name="student_birth_before_admission",
            )
        ]

    def clean(self):
        if self.birth_date and self.admitted_at and self.birth_date >= self.admitted_at:
            raise ValidationError(
                {"birth_date": "Дата рождения должна быть раньше даты зачисления."}
            )
        if (
            self.pk
            and self.admitted_at
            and self.enrollments.filter(started_on__lt=self.admitted_at).exists()
        ):
            raise ValidationError(
                {
                    "admitted_at": "До этой даты студент уже учился в группе. Проверьте дату зачисления."
                }
            )

    def __str__(self):
        return " ".join(
            filter(None, [self.last_name, self.first_name, self.middle_name])
        )


class Enrollment(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Студент",
    )
    group = models.ForeignKey(
        StudyGroup,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Группа",
    )
    started_on = models.DateField("С какой даты")
    ended_on = models.DateField("По какую дату", null=True, blank=True)
    note = models.CharField("Основание перевода", max_length=200, blank=True)
    end_note = models.CharField(
        "Основание завершения обучения", max_length=250, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_on"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ended_on__isnull=True) | Q(ended_on__gte=F("started_on")),
                name="enrollment_dates_order",
            ),
            models.UniqueConstraint(
                fields=["student"],
                condition=Q(ended_on__isnull=True),
                name="student_one_open_enrollment",
            ),
        ]
        indexes = [models.Index(fields=["group", "started_on"])]

    def clean(self):
        if not self.student_id or not self.started_on:
            return
        others = Enrollment.objects.filter(student_id=self.student_id).exclude(
            pk=self.pk
        )
        if self.ended_on:
            others = others.filter(started_on__lte=self.ended_on)
        others = others.filter(
            Q(ended_on__isnull=True) | Q(ended_on__gte=self.started_on)
        )
        if others.exists():
            raise ValidationError("В указанные даты студент уже состоит в группе.")

    def __str__(self):
        return f"{self.student} — {self.group}"


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="teacher",
        verbose_name="Учётная запись",
        limit_choices_to={"role": "teacher"},
    )
    staff_number = models.CharField("Табельный номер", max_length=25, unique=True)
    department = models.CharField("Отделение", max_length=120)
    position = models.CharField("Должность", max_length=100, default="Преподаватель")
    qualification = models.CharField("Категория", max_length=100, blank=True)
    hired_on = models.DateField("Дата приёма")
    phone = models.CharField("Рабочий телефон", max_length=30, blank=True)
    is_active = models.BooleanField("Работает", default=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        verbose_name = "преподаватель"
        verbose_name_plural = "преподаватели"

    def clean(self):
        if self.user_id and self.user.role != "teacher":
            raise ValidationError({"user": "Нужна учётная запись преподавателя."})

    def __str__(self):
        return str(self.user)


class Discipline(models.Model):
    code = models.CharField("Код", max_length=25, unique=True)
    name = models.CharField("Название", max_length=160)
    description = models.TextField("Описание", max_length=1500)
    department = models.CharField("Отделение", max_length=120)
    hours = models.PositiveSmallIntegerField("Объём, академических часов")
    assessment = models.CharField(
        "Форма контроля",
        max_length=15,
        choices=[("exam", "Экзамен"), ("credit", "Зачёт")],
    )
    lesson_type = models.CharField(
        "Основной вид занятий", max_length=60, default="Практическое занятие"
    )
    is_active = models.BooleanField("Преподаётся", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "дисциплина"
        verbose_name_plural = "дисциплины"
        constraints = [
            models.CheckConstraint(
                condition=Q(hours__gt=0), name="discipline_positive_hours"
            )
        ]

    def __str__(self):
        return self.name


class TeachingAssignment(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name="Преподаватель",
    )
    group = models.ForeignKey(
        StudyGroup,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name="Группа",
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name="Дисциплина",
    )
    started_on = models.DateField("Начало периода")
    ended_on = models.DateField("Конец периода")
    is_active = models.BooleanField("Действует", default=True)

    class Meta:
        ordering = ["group__code", "discipline__name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ended_on__gte=F("started_on")),
                name="assignment_dates_order",
            ),
            models.UniqueConstraint(
                fields=["teacher", "group", "discipline", "started_on"],
                name="unique_teaching_assignment",
            ),
        ]

    def clean(self):
        if self.pk and self.started_on and self.ended_on:
            outside = self.lessons.filter(
                Q(date__lt=self.started_on) | Q(date__gt=self.ended_on)
            )
            if outside.exists():
                raise ValidationError(
                    "Вне указанного периода остаются занятия. Проверьте даты назначения."
                )

    def __str__(self):
        return f"{self.group} · {self.discipline} · {self.teacher}"


class Lesson(models.Model):
    STATES = [
        ("planned", "Запланировано"),
        ("completed", "Проведено"),
        ("cancelled", "Отменено"),
    ]
    assignment = models.ForeignKey(
        TeachingAssignment,
        on_delete=models.PROTECT,
        related_name="lessons",
        verbose_name="Назначение",
    )
    date = models.DateField("Дата")
    starts_at = models.TimeField("Начало")
    ends_at = models.TimeField("Окончание")
    topic = models.CharField("Тема", max_length=200)
    room = models.CharField("Аудитория", max_length=30)
    state = models.CharField(
        "Состояние", max_length=12, choices=STATES, default="planned"
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField("Причина отмены", max_length=250, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancelled_lessons",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_lessons",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "starts_at", "id"]
        verbose_name = "занятие"
        verbose_name_plural = "занятия"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="lesson_time_order"
            ),
            models.CheckConstraint(
                condition=Q(state__in=["planned", "completed", "cancelled"]),
                name="lesson_state_valid",
            ),
        ]
        indexes = [models.Index(fields=["date", "state"])]

    def clean(self):
        if not self.assignment_id or not self.date:
            return
        if not self.assignment.started_on <= self.date <= self.assignment.ended_on:
            raise ValidationError(
                {"date": "Дата выходит за период назначения преподавателя."}
            )
        if self.state == "cancelled" or not self.starts_at or not self.ends_at:
            return
        overlaps = (
            Lesson.objects.filter(
                date=self.date, starts_at__lt=self.ends_at, ends_at__gt=self.starts_at
            )
            .exclude(pk=self.pk)
            .exclude(state="cancelled")
        )
        if overlaps.filter(assignment__group_id=self.assignment.group_id).exists():
            raise ValidationError("У группы уже есть занятие в это время.")
        if overlaps.filter(assignment__teacher_id=self.assignment.teacher_id).exists():
            raise ValidationError("Преподаватель занят в это время.")

    def __str__(self):
        return f"{self.date:%d.%m.%Y} · {self.assignment.group} · {self.assignment.discipline}"
