from datetime import date, time, timedelta
from getpass import getpass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from college.models import (
    Discipline,
    Enrollment,
    Lesson,
    Specialty,
    Student,
    StudyGroup,
    Teacher,
    TeachingAssignment,
)
from journal.models import AbsenceReason, Attendance, AttendanceChange
from journal.services import snapshot

SURNAMES = [
    "Соколов",
    "Иванов",
    "Петров",
    "Смирнов",
    "Кузнецов",
    "Волков",
    "Новиков",
    "Морозов",
    "Попов",
    "Орлов",
    "Белов",
    "Лебедев",
    "Козлов",
    "Зайцев",
    "Павлов",
    "Семёнов",
    "Голубев",
    "Фёдоров",
    "Макаров",
    "Егоров",
]
NAMES = [
    "Алексей",
    "Дмитрий",
    "Илья",
    "Михаил",
    "Андрей",
    "Иван",
    "Никита",
    "Кирилл",
    "Денис",
    "Максим",
]
SUBJECTS = [
    "Основы программирования",
    "Базы данных",
    "Информационные системы",
    "Экономика организации",
    "Математика",
    "Компьютерные сети",
]


class Command(BaseCommand):
    help = "Добавляет начальные записи и пользователей для проверки приложения."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password-file", help="Файл с паролем создаваемых учётных записей"
        )
        parser.add_argument("--date", help="Дата начальных записей в формате ГГГГ-ММ-ДД")

    @transaction.atomic
    def handle(self, *args, **options):
        password = (
            Path(options["password_file"]).read_text(encoding="utf-8").strip()
            if options["password_file"]
            else getpass("Пароль для создаваемых учётных записей: ")
        )
        if len(password) < 12:
            raise CommandError("Используйте пароль длиной не менее 12 символов.")
        today = (
            date.fromisoformat(options["date"])
            if options["date"]
            else timezone.localdate()
        )
        month = today.replace(day=1)

        def user(username, role, first_name, last_name):
            record, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": username + "@example.com",
                },
            )
            if created:
                record.set_password(password)
                record.save()
            return record

        administrator = user("administrator", "admin", "Илья", "Андрушкевич")
        curators = [
            user(f"curator{i+1}", "curator", NAMES[i], SURNAMES[i]) for i in range(4)
        ]
        teachers = []
        for i in range(8):
            account = user(f"teacher{i+1}", "teacher", NAMES[i + 2], SURNAMES[i + 5])
            teacher, _ = Teacher.objects.get_or_create(
                user=account,
                defaults={
                    "staff_number": f"Т-{i+1:03}",
                    "department": "Информационные технологии",
                    "qualification": "Первая категория",
                    "hired_on": date(2023, 9, 1),
                },
            )
            teachers.append(teacher)
        specialty, _ = Specialty.objects.get_or_create(
            code="09.02.07",
            defaults={
                "name": "Информационные системы и программирование",
                "qualification": "Программист",
                "duration": 46,
            },
        )
        disciplines = []
        for i, name in enumerate(SUBJECTS):
            record, _ = Discipline.objects.get_or_create(
                code=f"Д-{i+1:02}",
                defaults={
                    "name": name,
                    "description": "Практические задания, разбор примеров и самостоятельная работа по дисциплине «"
                    + name
                    + "».",
                    "department": "Информационные технологии",
                    "hours": 72,
                    "assessment": "exam" if i % 2 == 0 else "credit",
                },
            )
            disciplines.append(record)
        reason, _ = AbsenceReason.objects.get_or_create(
            code="illness",
            defaults={
                "name": "Болезнь",
                "description": "Причина подтверждена куратором.",
            },
        )
        for code, name in [
            ("event", "Учебное мероприятие"),
            ("family", "Семейные обстоятельства"),
        ]:
            AbsenceReason.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": "Отсутствие согласовано с учебной частью.",
                },
            )
        for group_index in range(4):
            group, _ = StudyGroup.objects.get_or_create(
                code=f"ИС-{21+group_index}",
                defaults={
                    "name": f"Информационные системы, группа {group_index+1}",
                    "specialty": specialty,
                    "admission_year": today.year - 1,
                    "graduation_year": today.year + 3,
                    "curator": curators[group_index],
                },
            )
            students = []
            for i in range(20):
                student, _ = Student.objects.get_or_create(
                    number=f"{group.code}-{i+1:03}",
                    defaults={
                        "last_name": SURNAMES[i],
                        "first_name": NAMES[(i + group_index) % 10],
                        "middle_name": "Александрович",
                        "birth_date": date(2008, i % 12 + 1, i % 25 + 1),
                        "admitted_at": date(today.year - 1, 9, 1),
                        "email": f"student{group_index+1}_{i+1}@example.com",
                    },
                )
                Enrollment.objects.get_or_create(
                    student=student, group=group, started_on=student.admitted_at
                )
                students.append(student)
            for slot in range(2):
                assignment, _ = TeachingAssignment.objects.get_or_create(
                    group=group,
                    teacher=teachers[group_index * 2 + slot],
                    discipline=disciplines[(group_index * 2 + slot) % len(disciplines)],
                    started_on=month,
                    defaults={"ended_on": date(today.year, 12, 31)},
                )
                current = month
                while current <= today + timedelta(days=5):
                    if current.weekday() < 5:
                        completed = current < today - timedelta(days=1)
                        lesson, created = Lesson.objects.get_or_create(
                            assignment=assignment,
                            date=current,
                            starts_at=time(9 + 2 * slot, 0),
                            defaults={
                                "ends_at": time(10 + 2 * slot, 30),
                                "topic": f"Практическое занятие {current.day}: работа с примерами",
                                "room": str(201 + group_index),
                                "state": "completed" if completed else "planned",
                                "closed_at": timezone.now() if completed else None,
                                "closed_by": (
                                    assignment.teacher.user if completed else None
                                ),
                            },
                        )
                        if created and completed:
                            marks = []
                            for i, student in enumerate(students):
                                variant = (current.day + i + group_index) % 17
                                status = (
                                    "absent"
                                    if variant == 0
                                    else (
                                        "late"
                                        if variant == 1
                                        else "excused" if variant == 2 else "present"
                                    )
                                )
                                marks.append(
                                    Attendance(
                                        lesson=lesson,
                                        student=student,
                                        status=status,
                                        late_minutes=10 if status == "late" else 0,
                                        reason=reason if status == "excused" else None,
                                        updated_by=assignment.teacher.user,
                                    )
                                )
                            Attendance.objects.bulk_create(marks)
                            AttendanceChange.objects.bulk_create(
                                [
                                    AttendanceChange(
                                        attendance=mark,
                                        author=administrator,
                                        after=snapshot(mark),
                                        explanation="Начальное заполнение базы",
                                    )
                                    for mark in marks
                                ]
                            )
                    current += timedelta(days=1)
        self.stdout.write(
            f"Созданы записи: {StudyGroup.objects.count()} группы, {Student.objects.count()} студентов, {Lesson.objects.count()} занятия."
        )
        self.stdout.write(
            "Пользователи: administrator, teacher1–teacher8, curator1–curator4. Существующие пароли и отметки не перезаписаны."
        )
