from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import IntegrityError
from django.http import HttpResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import admin_required
from .access import visible_disciplines, visible_groups, visible_lessons, visible_students
from .common import form_page, page_records, save_form
from .forms import AssignmentForm, CancellationForm, DisciplineForm, GroupForm, ImportForm, LessonForm, SpecialtyForm, StudentCreateForm, StudentForm, TeacherForm, TransferForm
from .models import Discipline, Enrollment, Lesson, Specialty, Student, StudyGroup, Teacher, TeachingAssignment
from .services import cancel_lesson, save_lesson, transfer_student


@login_required
def students(request):
    records = visible_students(request.user)
    query = request.GET.get('q', '').strip()[:100]
    if query:
        records = records.filter(Q(last_name__icontains=query) | Q(first_name__icontains=query) | Q(number__icontains=query))
    return render(request, 'college/students.html', {'records': page_records(request, records), 'query': query, 'title': 'Студенты', 'section': 'students'})


@login_required
def student_detail(request, pk):
    student = get_object_or_404(visible_students(request.user), pk=pk)
    enrollment = student.enrollments.filter(group__in=visible_groups(request.user)).select_related('group')
    marks = student.marks.filter(lesson__in=visible_lessons(request.user)).select_related('lesson__assignment__discipline').order_by('-lesson__date')[:30]
    return render(request, 'college/student.html', {'student': student, 'enrollments': enrollment, 'marks': marks, 'title': str(student), 'section': 'students', 'breadcrumbs': [('Студенты', reverse('students'))]})


@admin_required
def student_edit(request, pk=None):
    record = get_object_or_404(Student, pk=pk) if pk else Student()
    form_class = StudentForm if pk else StudentCreateForm
    form = form_class(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            student = form.save()
            if not pk:
                Enrollment.objects.create(student=student, group=form.cleaned_data['group'], started_on=student.admitted_at)
        messages.success(request, 'Сведения о студенте сохранены.')
        return redirect('student_detail', pk=student.pk)
    return form_page(request, form, 'Изменить студента' if pk else 'Добавить студента', 'students', 'students')


@admin_required
def student_transfer(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form = TransferForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            transfer_student(student, form.cleaned_data['group'], form.cleaned_data['date'], form.cleaned_data['note'])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Перевод сохранён. Прежний журнал остался без изменений.')
            return redirect('student_detail', pk=pk)
    return form_page(request, form, f'Перевод: {student}', 'students', 'students')


@login_required
def groups(request):
    return render(request, 'college/groups.html', {'records': visible_groups(request.user), 'title': 'Группы', 'section': 'groups'})


@login_required
def group_detail(request, pk):
    group = get_object_or_404(visible_groups(request.user), pk=pk)
    date = timezone.localdate()
    records = Enrollment.objects.filter(group=group, started_on__lte=date).filter(Q(ended_on__isnull=True) | Q(ended_on__gte=date)).select_related('student')
    lessons = visible_lessons(request.user).filter(assignment__group=group)[:12]
    return render(request, 'college/group.html', {'group': group, 'records': records, 'lessons': lessons, 'title': str(group), 'section': 'groups', 'breadcrumbs': [('Группы', reverse('groups'))]})


@admin_required
def group_edit(request, pk=None):
    record = get_object_or_404(StudyGroup, pk=pk) if pk else StudyGroup()
    form = GroupForm(request.POST or None, instance=record)
    return save_form(request, form, 'Изменить группу' if pk else 'Добавить группу', 'groups', 'groups')


@login_required
def disciplines(request):
    return render(request, 'college/disciplines.html', {'records': visible_disciplines(request.user), 'title': 'Дисциплины', 'section': 'disciplines'})


@admin_required
def discipline_edit(request, pk=None):
    record = get_object_or_404(Discipline, pk=pk) if pk else Discipline()
    return save_form(request, DisciplineForm(request.POST or None, instance=record), 'Дисциплина', 'disciplines', 'disciplines')


@admin_required
def teachers(request):
    return render(request, 'college/teachers.html', {'records': Teacher.objects.select_related('user'), 'title': 'Преподаватели', 'section': 'teachers'})


@admin_required
def teacher_edit(request, pk=None):
    record = get_object_or_404(Teacher, pk=pk) if pk else Teacher()
    return save_form(request, TeacherForm(request.POST or None, instance=record), 'Преподаватель', 'teachers', 'teachers')


@login_required
def lessons(request):
    from journal.filters import JournalFilter
    form = JournalFilter(request.GET, request.user)
    records = form.filter_lessons(visible_lessons(request.user))
    return render(request, 'college/lessons.html', {'filter': form, 'records': page_records(request, records), 'title': 'Занятия', 'section': 'lessons', 'subtitle': 'Расписание и состояние журналов за выбранный период'})


@admin_required
def lesson_edit(request, pk=None):
    record = get_object_or_404(Lesson, pk=pk) if pk else Lesson()
    form = LessonForm(request.POST or None, instance=record)
    if pk and record.marks.exists():
        for name in ['assignment', 'date', 'starts_at', 'ends_at']:
            form.fields[name].disabled = True
    if request.method == 'POST' and form.is_valid():
        try:
            save_lesson(form)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
        else:
            messages.success(request, 'Занятие сохранено.')
            return redirect('lessons')
    return form_page(request, form, 'Изменить занятие' if pk else 'Новое занятие', 'lessons', 'lessons')


@admin_required
def lesson_cancel(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    form = CancellationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            cancel_lesson(request.user, pk, form.cleaned_data['reason'])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Занятие отменено.')
            return redirect('lesson_journal', pk=pk)
    return form_page(request, form, f'Отмена занятия: {lesson}', 'lessons', 'lessons')


@login_required
def dashboard(request):
    from journal.filters import JournalFilter
    from journal.statistics import report_data
    today = timezone.localdate()
    data = report_data(request.user, JournalFilter({}, request.user))
    data.update({
        'title': 'Обзор', 'section': 'dashboard', 'subtitle': today.strftime('%d.%m.%Y'),
        'records': visible_lessons(request.user).filter(date=today).order_by('starts_at'),
        'pending': visible_lessons(request.user).filter(date__lte=today, state='planned')[:6],
        'group_count': visible_groups(request.user).count(),
        'student_count': visible_students(request.user).count(),
    })
    return render(request, 'college/dashboard.html', data)


@login_required
def help_page(request):
    return render(request, 'college/help.html', {'title': 'Справка', 'section': 'help'})


@admin_required
def management(request):
    return render(request, 'college/management.html', {'title': 'Управление', 'section': 'management'})


@admin_required
def specialties(request):
    return render(request, 'college/specialties.html', {'records': Specialty.objects.all(), 'title': 'Специальности', 'section': 'management'})


@admin_required
def specialty_edit(request, pk=None):
    record = get_object_or_404(Specialty, pk=pk) if pk else Specialty()
    return save_form(request, SpecialtyForm(request.POST or None, instance=record), 'Специальность', 'management', 'specialties')


@admin_required
def assignments(request):
    records = TeachingAssignment.objects.select_related('teacher__user', 'group', 'discipline')
    return render(request, 'college/assignments.html', {'records': records, 'title': 'Назначения преподавателей', 'section': 'management'})


@admin_required
def assignment_edit(request, pk=None):
    record = get_object_or_404(TeachingAssignment, pk=pk) if pk else TeachingAssignment()
    form = AssignmentForm(request.POST or None, instance=record)
    if pk and record.lessons.exists():
        for name in ['teacher', 'group', 'discipline']:
            form.fields[name].disabled = True
    return save_form(request, form, 'Назначение преподавателя', 'management', 'assignments')


@admin_required
def student_import(request):
    from .importing import import_students, read_students
    form = ImportForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    preview = None
    if request.method == 'POST' and request.POST.get('action') == 'confirm':
        saved = request.session.get('student_import')
        if not saved or timezone.now().timestamp() - saved['created'] > 900:
            messages.error(request, 'Предварительная проверка устарела. Загрузите файл заново.')
        else:
            group = get_object_or_404(StudyGroup, pk=saved['group'], is_active=True)
            try:
                count = import_students(saved['records'], group)
            except (ValidationError, IntegrityError):
                messages.error(request, 'Список не загружен: данные уже изменились. Проверьте номера студентов и повторите загрузку.')
            else:
                request.session.pop('student_import', None)
                messages.success(request, f'Добавлено студентов: {count}.')
                return redirect('students')
    elif request.method == 'POST' and form.is_valid():
        request.session.pop('student_import', None)
        try:
            preview = read_students(form.cleaned_data['file'])
        except ValidationError as error:
            form.add_error('file', error)
        else:
            request.session['student_import'] = {'records': preview, 'group': form.cleaned_data['group'].pk, 'created': timezone.now().timestamp()}
    return render(request, 'college/import.html', {'form': form, 'preview': preview, 'title': 'Импорт студентов', 'section': 'management'})


@admin_required
def import_sample(request):
    from .importing import HEADERS
    text = ';'.join(HEADERS) + '\nDEMO-901;Соколов;Алексей;Игоревич;2008-05-12;student901@example.com;2026-09-01\n'
    response = HttpResponse('\ufeff' + text, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="students_sample.csv"'
    return response
