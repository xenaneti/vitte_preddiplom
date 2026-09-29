from django import forms
from django.db.models import Q

from .models import AbsenceReason, Attendance


class MarkForm(forms.Form):
    status = forms.ChoiceField(label='Отметка', choices=[('', 'Не отмечено')] + Attendance.STATUSES, required=False)
    late_minutes = forms.IntegerField(label='Минут опоздания', min_value=0, max_value=180, required=False, initial=0)
    reason = forms.ModelChoiceField(label='Причина', queryset=AbsenceReason.objects.all(), required=False, empty_label='Не указана')
    comment = forms.CharField(label='Комментарий', max_length=300, required=False)
    explanation = forms.CharField(label='Причина исправления', max_length=300, required=False)
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=0, initial=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].queryset = AbsenceReason.objects.filter(Q(is_active=True) | Q(pk=self.initial.get('reason')))

    def clean(self):
        data = super().clean()
        status = data.get('status')
        minutes = data.get('late_minutes') or 0
        data['late_minutes'] = minutes
        if status == 'late' and minutes == 0:
            self.add_error('late_minutes', 'Укажите от 1 до 180 минут.')
        if status != 'late' and minutes:
            self.add_error('late_minutes', 'Минуты указываются только при опоздании.')
        if status == 'excused' and not data.get('reason'):
            self.add_error('reason', 'Выберите причину пропуска.')
        if status != 'excused' and data.get('reason'):
            self.add_error('reason', 'Причина указывается для уважительного пропуска.')
        return data


class ReasonForm(forms.ModelForm):
    class Meta:
        model = AbsenceReason
        fields = ['code', 'name', 'description', 'needs_confirmation', 'is_active']
