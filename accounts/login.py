from hashlib import sha256

from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods


def counter_key(request, username):
    address = request.META.get("REMOTE_ADDR", "")
    value = f"{address}:{username.strip().lower()}"
    return "login:" + sha256(value.encode()).hexdigest()


@never_cache
@require_http_methods(["GET", "POST"])
def login(request):
    form = AuthenticationForm(
        request, data=request.POST if request.method == "POST" else None
    )
    target = request.POST.get("next", request.GET.get("next", ""))
    status = 200
    if request.method == "POST":
        key = counter_key(request, request.POST.get("username", ""))
        failures = cache.get(key, 0)
        if failures >= 5:
            form.add_error(
                None, "Слишком много попыток. Повторите вход через 15 минут."
            )
            status = 429
        elif form.is_valid():
            cache.delete(key)
            auth_login(request, form.get_user())
            if url_has_allowed_host_and_scheme(
                target, {request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(target)
            return redirect("dashboard")
        else:
            cache.set(key, failures + 1, timeout=15 * 60)
    response = render(
        request,
        "accounts/login.html",
        {"form": form, "next": target, "title": "Вход в журнал"},
        status=status,
    )
    if status == 429:
        response["Retry-After"] = "900"
    return response
