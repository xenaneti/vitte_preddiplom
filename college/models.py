from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Specialty(models.Model):
    code = models.CharField('Код', max_length=20, unique=True)
    name = models.CharField('Название', max_length=180)
    qualification = models.CharField('Квалификация', max_length=120)
    duration = models.PositiveSmallIntegerField('Срок обучения, месяцев', default=46)
    is_active = models.BooleanField('Действует', default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'специальность'
        verbose_name_plural = 'специальности'

    def __str__(self):
        return f'{self.code} — {self.name}'


class StudyGroup(models.Model):
    code = models.CharField('Группа', max_length=30, unique=True)
    name = models.CharField('Наименование', max_length=150)
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, verbose_name='Специальность')
    admission_year = models.PositiveSmallIntegerField('Год набора')
    graduation_year = models.PositiveSmallIntegerField('Год выпуска')
    study_form = models.CharField('Форма обучения', max_length=20, choices=[('full', 'Очная'), ('part', 'Очно-заочная')], default='full')
    curator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='curated_groups', verbose_name='Куратор', limit_choices_to={'role': 'curator'})
    is_active = models.BooleanField('Действует', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'группа'
        verbose_name_plural = 'группы'
        constraints = [models.CheckConstraint(condition=Q(graduation_year__gt=F('admission_year')), name='group_years_order')]

    def clean(self):
        if self.curator_id and self.curator.role != 'curator':
            raise ValidationError({'curator': 'Выберите пользователя с ролью куратора.'})

    def __str__(self):
        return self.code


class Student(models.Model):
    number = models.CharField('Номер студента', max_length=25, unique=True)
    last_name = models.CharField('Фамилия', max_length=100)
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    birth_date = models.DateField('Дата рождения')
    email = models.EmailField('Почта', blank=True)
    admitted_at = models.DateField('Дата зачисления')
    is_active = models.BooleanField('Обучается', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name', 'id']
        verbose_name = 'студент'
        verbose_name_plural = 'студенты'

    def clean(self):
        if self.birth_date and self.admitted_at and self.birth_date >= self.admitted_at:
            raise ValidationError({'birth_date': 'Дата рождения должна быть раньше даты зачисления.'})

    def __str__(self):
        return ' '.join(filter(None, [self.last_name, self.first_name, self.middle_name]))


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='enrollments', verbose_name='Студент')
    group = models.ForeignKey(StudyGroup, on_delete=models.PROTECT, related_name='enrollments', verbose_name='Группа')
    started_on = models.DateField('С какой даты')
    ended_on = models.DateField('По какую дату', null=True, blank=True)
    note = models.CharField('Основание перевода', max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_on']
        constraints = [models.CheckConstraint(condition=Q(ended_on__isnull=True) | Q(ended_on__gte=F('started_on')), name='enrollment_dates_order')]
        indexes = [models.Index(fields=['group', 'started_on'])]

    def clean(self):
        if not self.student_id or not self.started_on:
            return
        others = Enrollment.objects.filter(student_id=self.student_id).exclude(pk=self.pk)
        if self.ended_on:
            others = others.filter(started_on__lte=self.ended_on)
        others = others.filter(Q(ended_on__isnull=True) | Q(ended_on__gte=self.started_on))
        if others.exists():
            raise ValidationError('В указанные даты студент уже состоит в группе.')

    def __str__(self):
        return f'{self.student} — {self.group}'
