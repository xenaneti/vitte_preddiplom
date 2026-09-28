from django import forms
from django.utils import timezone

from accounts.models import User
from .models import Discipline, Enrollment, Lesson, Specialty, Student, StudyGroup, Teacher, TeachingAssignment


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%d', **kwargs)


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['number', 'last_name', 'first_name', 'middle_name', 'birth_date', 'email', 'admitted_at', 'is_active']
        widgets = {'birth_date': DateInput(), 'admitted_at': DateInput()}


class StudentCreateForm(StudentForm):
    group = forms.ModelChoiceField(label='Группа', queryset=StudyGroup.objects.filter(is_active=True))


class GroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ['code', 'name', 'specialty', 'admission_year', 'graduation_year', 'study_form', 'curator', 'is_active']


class SpecialtyForm(forms.ModelForm):
    class Meta:
        model = Specialty
        fields = ['code', 'name', 'qualification', 'duration', 'is_active']


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['user', 'staff_number', 'department', 'position', 'qualification', 'hired_on', 'phone', 'is_active']
        widgets = {'hired_on': DateInput()}


class DisciplineForm(forms.ModelForm):
    class Meta:
        model = Discipline
        fields = ['code', 'name', 'description', 'department', 'hours', 'assessment', 'lesson_type', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = TeachingAssignment
        fields = ['teacher', 'group', 'discipline', 'started_on', 'ended_on', 'is_active']
        widgets = {'started_on': DateInput(), 'ended_on': DateInput()}


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['assignment', 'date', 'starts_at', 'ends_at', 'topic', 'room']
        widgets = {'date': DateInput(), 'starts_at': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'), 'ends_at': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignment'].queryset = TeachingAssignment.objects.filter(is_active=True).select_related('teacher__user', 'group', 'discipline')


class TransferForm(forms.Form):
    group = forms.ModelChoiceField(label='Новая группа', queryset=StudyGroup.objects.filter(is_active=True))
    date = forms.DateField(label='Дата перевода', widget=DateInput(), initial=timezone.localdate)
    note = forms.CharField(label='Основание', max_length=200)


class ImportForm(forms.Form):
    group = forms.ModelChoiceField(label='Группа', queryset=StudyGroup.objects.filter(is_active=True))
    file = forms.FileField(label='Список студентов в CSV', help_text='UTF-8, разделитель «;», не более 500 студентов и 1 МБ.')
