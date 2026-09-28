from django.contrib import admin
from django.urls import include, path

from support import views as support_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('college.urls')),
    path('', include('journal.urls')),
    path('feedback/', support_views.tickets, name='tickets'),
    path('feedback/<int:pk>/', support_views.ticket_detail, name='ticket_detail'),
]
