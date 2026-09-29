from django.db.models import Q

from .models import (
    Discipline,
    Enrollment,
    Lesson,
    Student,
    StudyGroup,
    TeachingAssignment,
)


def visible_groups(user):
    groups = StudyGroup.objects.select_related("specialty", "curator")
    if user.is_administrator:
        return groups
    if user.role == "curator":
        return groups.filter(curator=user)
    return groups.filter(assignments__teacher__user=user).distinct()


def visible_assignments(user):
    assignments = TeachingAssignment.objects.select_related(
        "group", "discipline", "teacher__user"
    )
    if user.is_administrator:
        return assignments
    if user.role == "curator":
        return assignments.filter(group__curator=user)
    return assignments.filter(teacher__user=user)


def visible_lessons(user):
    return Lesson.objects.filter(
        assignment__in=visible_assignments(user)
    ).select_related(
        "assignment__group", "assignment__discipline", "assignment__teacher__user"
    )


def visible_students(user):
    if user.is_administrator:
        return Student.objects.all()
    return Student.objects.filter(
        enrollments__group__in=visible_groups(user)
    ).distinct()


def visible_disciplines(user):
    if user.is_administrator:
        return Discipline.objects.all()
    return Discipline.objects.filter(
        assignments__in=visible_assignments(user)
    ).distinct()


def lesson_students(lesson):
    enrollment = Enrollment.objects.filter(
        group=lesson.assignment.group, started_on__lte=lesson.date
    )
    enrollment = enrollment.filter(
        Q(ended_on__isnull=True) | Q(ended_on__gte=lesson.date)
    )
    return Student.objects.filter(enrollments__in=enrollment).distinct()


def can_mark(user, lesson):
    return user.is_administrator or (
        user.role == "teacher" and lesson.assignment.teacher.user_id == user.pk
    )
