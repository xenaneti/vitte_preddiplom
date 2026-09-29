from django import forms
from django.contrib.auth import password_validation

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "middle_name", "email"]


class UserForm(forms.ModelForm):
    password = forms.CharField(
        label="Новый пароль",
        required=False,
        widget=forms.PasswordInput,
        help_text="При изменении оставьте пустым, чтобы сохранить пароль.",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "last_name",
            "first_name",
            "middle_name",
            "email",
            "role",
            "is_active",
        ]

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor

    def clean(self):
        data = super().clean()
        password = data.get("password")
        if not self.instance.pk and not password:
            self.add_error("password", "Укажите пароль для новой учётной записи.")
        if password:
            password_validation.validate_password(password, self.instance)
        if self.instance.pk:
            if self.instance.pk == self.actor.pk and (
                not data.get("is_active") or data.get("role") != "admin"
            ):
                raise forms.ValidationError(
                    "Нельзя отключить себя или изменить собственную роль."
                )
            if hasattr(self.instance, "teacher") and data.get("role") != "teacher":
                self.add_error(
                    "role",
                    "У пользователя есть карточка преподавателя. Его роль менять нельзя.",
                )
            if self.instance.curated_groups.exists() and data.get("role") != "curator":
                self.add_error("role", "Сначала назначьте группам другого куратора.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
