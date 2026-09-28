from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ReplyForm, TicketForm
from .models import Ticket


def accessible_tickets(user):
    records = Ticket.objects.select_related('author', 'replied_by')
    return records if user.is_administrator else records.filter(author=user)


@login_required
def tickets(request):
    form = TicketForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        ticket = form.save(commit=False)
        ticket.author = request.user
        ticket.save()
        messages.success(request, 'Обращение отправлено администратору.')
        return redirect('ticket_detail', pk=ticket.pk)
    return render(request, 'support/list.html', {'form': form, 'records': accessible_tickets(request.user), 'title': 'Обратная связь', 'section': 'tickets'})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(accessible_tickets(request.user), pk=pk)
    form = None
    if request.user.is_administrator:
        form = ReplyForm(request.POST if request.method == 'POST' else None, instance=ticket)
        if request.method == 'POST' and form.is_valid():
            ticket = form.save(commit=False)
            ticket.replied_by = request.user
            ticket.save()
            messages.success(request, 'Ответ сохранён.')
            return redirect('ticket_detail', pk=pk)
    return render(request, 'support/ticket.html', {'ticket': ticket, 'form': form, 'title': f'Обращение № {ticket.pk}', 'section': 'tickets', 'breadcrumbs': [('Обратная связь', reverse('tickets'))]})
