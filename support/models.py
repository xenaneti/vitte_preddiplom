from django.db import models
from django.conf import settings


class Ticket(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tickets')
    subject = models.CharField('Тема', max_length=150)
    text = models.TextField('Сообщение', max_length=3000)
    status = models.CharField('Состояние', max_length=10, choices=[('new', 'Новое'), ('active', 'В работе'), ('closed', 'Закрыто')], default='new')
    reply = models.TextField('Ответ', max_length=3000, blank=True)
    replied_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='answered_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=models.Q(status__in=['new', 'active', 'closed']), name='ticket_status_valid')]

    def __str__(self):
        return self.subject
