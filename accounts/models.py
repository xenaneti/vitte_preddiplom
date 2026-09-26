from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [('admin', 'Администратор'), ('teacher', 'Преподаватель'), ('curator', 'Куратор')]
    role = models.CharField('Роль', max_length=12, choices=ROLES, default='teacher')
    middle_name = models.CharField('Отчество', max_length=100, blank=True)

    @property
    def is_administrator(self):
        return self.is_active and (self.is_superuser or self.role == 'admin')

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'admin'
        self.is_staff = self.role == 'admin'
        super().save(*args, **kwargs)

    def get_full_name(self):
        return ' '.join(filter(None, [self.last_name, self.first_name, self.middle_name])) or self.username

    def __str__(self):
        return self.get_full_name()
