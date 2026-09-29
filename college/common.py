from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse


def form_page(request, form, title, section, back):
    return render(
        request,
        "form.html",
        {
            "form": form,
            "title": title,
            "section": section,
            "back_url": reverse(back),
            "breadcrumbs": [("Назад к списку", reverse(back))],
        },
    )


def save_form(request, form, title, section, back):
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Изменения сохранены.")
        return redirect(back)
    return form_page(request, form, title, section, back)


def page_records(request, records):
    return Paginator(records, 25).get_page(request.GET.get("page"))
