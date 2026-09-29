from django import forms
from django.db.models import Q
from django.utils import timezone

from .access import visible_groups


class StudentFilter(forms.Form):
    q = forms.CharField(label="Фамилия, имя или номер", max_length=100, required=False)
    group = forms.ModelChoiceField(
        label="Текущая группа",
        queryset=None,
        required=False,
        empty_label="Все доступные",
    )
    state = forms.ChoiceField(
        label="Состояние",
        required=False,
        choices=[("", "Все"), ("active", "Обучается"), ("archive", "Архив")],
    )

    def __init__(self, data, user):
        super().__init__(data)
        self.fields["group"].queryset = visible_groups(user)

    def filter_students(self, records):
        if not self.is_valid():
            return records.none()
        data = self.cleaned_data
        if data["q"]:
            records = records.filter(
                Q(last_name__icontains=data["q"])
                | Q(first_name__icontains=data["q"])
                | Q(number__icontains=data["q"])
            )
        if data["group"]:
            date = timezone.localdate()
            records = records.filter(
                Q(enrollments__ended_on__isnull=True)
                | Q(enrollments__ended_on__gte=date),
                enrollments__group=data["group"],
                enrollments__started_on__lte=date,
            )
        if data["state"]:
            records = records.filter(is_active=data["state"] == "active")
        return records.distinct()
