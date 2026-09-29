from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return HttpResponse("unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")


def not_found(request, exception):
    return render(
        request,
        "error.html",
        {
            "title": "Страница не найдена",
            "text": "Проверьте адрес или вернитесь в журнал.",
            "code": 404,
        },
        status=404,
    )


def forbidden(request, exception):
    return render(
        request,
        "error.html",
        {
            "title": "Нет доступа",
            "text": "Этот раздел недоступен вашей учётной записи.",
            "code": 403,
        },
        status=403,
    )


def csrf_failure(request, reason=""):
    return render(
        request,
        "error.html",
        {
            "title": "Не удалось отправить форму",
            "text": "Обновите страницу и заполните форму ещё раз.",
            "code": 403,
        },
        status=403,
    )


def server_error(request):
    return render(
        request,
        "error.html",
        {
            "title": "Не удалось открыть страницу",
            "text": "Повторите попытку позже. Если ошибка остаётся, обратитесь к администратору.",
            "code": 500,
        },
        status=500,
    )
