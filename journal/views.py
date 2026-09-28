from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from college.access import can_mark, lesson_students, visible_lessons
from .filters import JournalFilter
from .forms import MarkForm
from .models import AttendanceChange
from .services import save_marks, snapshot
from .statistics import report_data
from .export import excel_report


@login_required
def journal(request):
    form = JournalFilter(request.GET, request.user)
    records = form.filter_lessons(visible_lessons(request.user))
    return render(request, 'journal/list.html', {'filter': form, 'records': records[:250], 'title': 'Журнал посещаемости', 'section': 'journal'})


@login_required
def lesson_journal(request, pk):
    lesson = get_object_or_404(visible_lessons(request.user), pk=pk)
    marks = {mark.student_id: mark for mark in lesson.marks.select_related('reason')}
    rows = []
    teacher_access = can_mark(request.user, lesson)
    for student in lesson_students(lesson):
        mark = marks.get(student.pk)
        initial = snapshot(mark)
        initial['reason'] = initial.pop('reason_id', None)
        initial['version'] = mark.version if mark else 0
        form = MarkForm(request.POST if request.method == 'POST' else None, prefix=f's{student.pk}', initial=initial)
        editable = teacher_access or (mark and mark.status in ('absent', 'excused'))
        if not editable or lesson.state == 'cancelled':
            for field in form.fields.values():
                field.disabled = True
        if not teacher_access and editable:
            form.fields['status'].choices = [('absent', 'Отсутствовал'), ('excused', 'Уважительная причина')]
            form.fields['late_minutes'].disabled = True
        for field in form.fields.values():
            field.widget.attrs['aria-label'] = f'{student}: {field.label}'
        rows.append({'student': student, 'form': form, 'mark': mark, 'editable': editable})
    if request.method == 'POST':
        valid = all([row['form'].is_valid() for row in rows])
        if valid:
            data = [(row['student'].pk, row['form'].cleaned_data) for row in rows]
            try:
                changes = save_marks(request.user, pk, data, close=request.POST.get('action') == 'close')
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                messages.success(request, f'Журнал сохранён. Изменено отметок: {changes}.')
                return redirect('lesson_journal', pk=pk)
    return render(request, 'journal/lesson.html', {'lesson': lesson, 'rows': rows, 'teacher_access': teacher_access, 'title': 'Журнал занятия', 'section': 'journal', 'breadcrumbs': [('Журнал', reverse('journal'))]})


@login_required
def history(request):
    form = JournalFilter(request.GET, request.user)
    lessons = form.filter_lessons(visible_lessons(request.user))
    records = AttendanceChange.objects.filter(attendance__lesson__in=lessons).select_related('author', 'attendance__student', 'attendance__lesson__assignment__discipline')
    if form.is_valid() and form.cleaned_data.get('student'):
        records = records.filter(attendance__student=form.cleaned_data['student'])
    return render(request, 'journal/history.html', {'records': records[:300], 'filter': form, 'title': 'История изменений', 'section': 'history'})


@login_required
def statistics(request):
    form = JournalFilter(request.GET, request.user)
    data = report_data(request.user, form)
    data.update({'filter': form, 'title': 'Статистика посещаемости', 'section': 'statistics'})
    return render(request, 'journal/statistics.html', data)


@login_required
def reports(request):
    form = JournalFilter(request.GET, request.user)
    data = report_data(request.user, form)
    if request.GET.get('format') == 'xlsx' and form.is_valid():
        if data['marks'].count() > 50000:
            messages.error(request, 'Слишком много отметок. Сократите период или выберите группу.')
        else:
            return excel_report(data, form.cleaned_data['date_from'], form.cleaned_data['date_to'])
    query = request.GET.copy()
    query['format'] = 'xlsx'
    data.update({'filter': form, 'title': 'Отчёты', 'section': 'reports', 'export_query': query.urlencode()})
    return render(request, 'journal/reports.html', data)
