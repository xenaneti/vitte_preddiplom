from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CollegeUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Колледж', {'fields': ('role', 'middle_name')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Колледж', {'fields': ('role',)}),)
    list_display = ('username', 'last_name', 'first_name', 'role', 'is_active')
