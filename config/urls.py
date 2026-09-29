from django.contrib import admin
from django.urls import include, path

from support import views as support_views
from . import views

handler403 = "config.views.forbidden"
handler404 = "config.views.not_found"
handler500 = "config.views.server_error"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("college.urls")),
    path("", include("journal.urls")),
    path("feedback/", support_views.tickets, name="tickets"),
    path("feedback/<int:pk>/", support_views.ticket_detail, name="ticket_detail"),
]
