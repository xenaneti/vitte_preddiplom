from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ProfileForm, UserForm
from .models import User
from .permissions import admin_required


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профиль сохранён.")
        return redirect("profile")
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "title": "Личный кабинет", "section": "profile"},
    )


@login_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Пароль изменён.")
        return redirect("profile")
    return render(
        request,
        "form.html",
        {
            "form": form,
            "title": "Смена пароля",
            "section": "profile",
            "breadcrumbs": [("Кабинет", reverse("profile"))],
            "back_url": reverse("profile"),
        },
    )


@admin_required
def users(request):
    records = User.objects.order_by("last_name", "username")
    return render(
        request,
        "accounts/users.html",
        {
            "records": records,
            "title": "Пользователи",
            "section": "management",
            "breadcrumbs": [("Управление", reverse("management"))],
        },
    )


@admin_required
def user_edit(request, pk=None):
    record = get_object_or_404(User, pk=pk) if pk else User()
    form = UserForm(request.POST or None, instance=record, actor=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Учётная запись сохранена.")
        return redirect("users")
    return render(
        request,
        "form.html",
        {
            "form": form,
            "title": "Учётная запись",
            "section": "management",
            "breadcrumbs": [("Пользователи", reverse("users"))],
            "back_url": reverse("users"),
        },
    )
