from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import admin_required
from .access import visible_disciplines, visible_groups, visible_lessons, visible_students
from .common import form_page, page_records, save_form
from .forms import AssignmentForm, DisciplineForm, GroupForm, LessonForm, SpecialtyForm, StudentCreateForm, StudentForm, TeacherForm, TransferForm
from .models import Discipline, Enrollment, Lesson, Specialty, Student, StudyGroup, Teacher, TeachingAssignment
from .services import transfer_student


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
