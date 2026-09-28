from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from .login import login

urlpatterns = [
    path('login/', login, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('account/', views.profile, name='profile'),
    path('account/password/', views.change_password, name='change_password'),
    path('users/', views.users, name='users'),
    path('users/new/', views.user_edit, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
]
