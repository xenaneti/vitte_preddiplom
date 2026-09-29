from django.urls import path
from . import views

urlpatterns = [
    path("journal/", views.journal, name="journal"),
    path("journal/group/", views.matrix, name="matrix"),
    path("journal/<int:pk>/", views.lesson_journal, name="lesson_journal"),
    path("statistics/", views.statistics, name="statistics"),
    path("reports/", views.reports, name="reports"),
    path("history/", views.history, name="history"),
    path("reasons/", views.reasons, name="reasons"),
    path("reasons/new/", views.reason_edit, name="reason_create"),
    path("reasons/<int:pk>/edit/", views.reason_edit, name="reason_edit"),
]
