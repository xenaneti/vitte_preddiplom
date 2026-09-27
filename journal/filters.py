from django import forms
from django.utils import timezone

from college.access import visible_disciplines, visible_groups, visible_students
from college.forms import DateInput


class JournalFilter(forms.Form):
    date_from = forms.DateField(label='С даты', widget=DateInput())
    date_to = forms.DateField(label='По дату', widget=DateInput())
    group = forms.ModelChoiceField(label='Группа', queryset=None, required=False, empty_label='Все доступные')
    discipline = forms.ModelChoiceField(label='Дисциплина', queryset=None, required=False, empty_label='Все доступные')
    student = forms.ModelChoiceField(label='Студент', queryset=None, required=False, empty_label='Все доступные')

    def __init__(self, data, user):
        today = timezone.localdate()
        values = data.copy()
        values.setdefault('date_from', today.replace(day=1).isoformat())
        values.setdefault('date_to', today.isoformat())
        super().__init__(values)
        self.fields['group'].queryset = visible_groups(user)
        self.fields['discipline'].queryset = visible_disciplines(user)
        self.fields['student'].queryset = visible_students(user)

    def clean(self):
        data = super().clean()
        start, end = data.get('date_from'), data.get('date_to')
        if start and end:
            if start > end:
                raise forms.ValidationError('Начало периода позже его окончания.')
            if (end - start).days > 366:
                raise forms.ValidationError('Выберите период не больше одного года.')
        return data

    def filter_lessons(self, records):
        if not self.is_valid():
            return records.none()
        data = self.cleaned_data
        records = records.filter(date__range=(data['date_from'], data['date_to']))
        if data.get('group'):
            records = records.filter(assignment__group=data['group'])
        if data.get('discipline'):
            records = records.filter(assignment__discipline=data['discipline'])
        if data.get('student'):
            records = records.filter(marks__student=data['student']).distinct()
        return records
