from django import forms
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from .models import (
    Discipline,
    Lesson,
    Specialty,
    Student,
    StudyGroup,
    Teacher,
    TeachingAssignment,
)


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%d", **kwargs)


class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].disabled = True
        self.fields["is_active"].help_text = (
            "Обучение завершается через карточку студента с указанием даты."
        )

    class Meta:
        model = Student
        fields = [
            "number",
            "last_name",
            "first_name",
            "middle_name",
            "birth_date",
            "email",
            "admitted_at",
            "is_active",
        ]
        widgets = {"birth_date": DateInput(), "admitted_at": DateInput()}


class StudentCreateForm(StudentForm):
    group = forms.ModelChoiceField(
        label="Группа", queryset=StudyGroup.objects.filter(is_active=True)
    )


class GroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["specialty"].queryset = Specialty.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.specialty_id)
        )
        self.fields["curator"].queryset = User.objects.filter(role="curator").filter(
            Q(is_active=True) | Q(pk=self.instance.curator_id)
        )

    class Meta:
        model = StudyGroup
        fields = [
            "code",
            "name",
            "specialty",
            "admission_year",
            "graduation_year",
            "study_form",
            "curator",
            "is_active",
        ]


class SpecialtyForm(forms.ModelForm):
    class Meta:
        model = Specialty
        fields = ["code", "name", "qualification", "duration", "is_active"]


class TeacherForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(role="teacher").filter(
            Q(is_active=True) | Q(pk=self.instance.user_id)
        )
        if self.instance.pk:
            self.fields["user"].disabled = True

    class Meta:
        model = Teacher
        fields = [
            "user",
            "staff_number",
            "department",
            "position",
            "qualification",
            "hired_on",
            "phone",
            "is_active",
        ]
        widgets = {"hired_on": DateInput()}


class DisciplineForm(forms.ModelForm):
    class Meta:
        model = Discipline
        fields = [
            "code",
            "name",
            "description",
            "department",
            "hours",
            "assessment",
            "lesson_type",
            "is_active",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class AssignmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["teacher"].queryset = Teacher.objects.filter(
            Q(is_active=True, user__is_active=True) | Q(pk=self.instance.teacher_id)
        ).select_related("user")
        self.fields["group"].queryset = StudyGroup.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.group_id)
        )
        self.fields["discipline"].queryset = Discipline.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.discipline_id)
        )

    class Meta:
        model = TeachingAssignment
        fields = [
            "teacher",
            "group",
            "discipline",
            "started_on",
            "ended_on",
            "is_active",
        ]
        widgets = {"started_on": DateInput(), "ended_on": DateInput()}


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["assignment", "date", "starts_at", "ends_at", "topic", "room"]
        widgets = {
            "date": DateInput(),
            "starts_at": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "ends_at": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available = Q(
            is_active=True,
            group__is_active=True,
            discipline__is_active=True,
            teacher__is_active=True,
            teacher__user__is_active=True,
        )
        self.fields["assignment"].queryset = TeachingAssignment.objects.filter(
            available | Q(pk=self.instance.assignment_id)
        ).select_related("teacher__user", "group", "discipline")


class TransferForm(forms.Form):
    group = forms.ModelChoiceField(
        label="Новая группа", queryset=StudyGroup.objects.filter(is_active=True)
    )
    date = forms.DateField(
        label="Дата перевода", widget=DateInput(), initial=timezone.localdate
    )
    note = forms.CharField(label="Основание", max_length=200)


class CancellationForm(forms.Form):
    reason = forms.CharField(
        label="Причина отмены", max_length=250, widget=forms.Textarea(attrs={"rows": 3})
    )


class WithdrawalForm(forms.Form):
    date = forms.DateField(
        label="Дата отчисления", widget=DateInput(), initial=timezone.localdate
    )
    note = forms.CharField(
        label="Основание", max_length=200, help_text="Например, номер и дата приказа."
    )


class ImportForm(forms.Form):
    group = forms.ModelChoiceField(
        label="Группа", queryset=StudyGroup.objects.filter(is_active=True)
    )
    file = forms.FileField(
        label="Список студентов в CSV",
        help_text="UTF-8, разделитель «;», не более 500 студентов и 1 МБ.",
    )
