from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('login/', LoginView.as_view(template_name='accounts/login.html', extra_context={'title': 'Вход в журнал'}), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('account/', views.profile, name='profile'),
    path('account/password/', views.change_password, name='change_password'),
    path('users/', views.users, name='users'),
    path('users/new/', views.user_edit, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
]
