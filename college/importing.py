import csv
from io import StringIO

from django.core.exceptions import ValidationError
from django.db import transaction

from .forms import StudentForm
from .models import Enrollment

HEADERS = [
    "number",
    "last_name",
    "first_name",
    "middle_name",
    "birth_date",
    "email",
    "admitted_at",
]


def read_students(upload):
    try:
        return parse_students(upload)
    except csv.Error:
        raise ValidationError(
            "Не удалось прочитать CSV. Проверьте кавычки и длину полей."
        )


def parse_students(upload):
    if upload.size > 1024 * 1024:
        raise ValidationError("Файл должен быть не больше 1 МБ.")
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("Сохраните CSV в кодировке UTF-8.")
    reader = csv.DictReader(StringIO(text), delimiter=";", strict=True)
    if reader.fieldnames != HEADERS:
        raise ValidationError(
            "Заголовки не совпадают с образцом. Используйте разделитель «;»."
        )
    records, errors, numbers = [], [], set()
    for row_number, row in enumerate(reader, 2):
        if row_number > 501:
            raise ValidationError("За один раз можно загрузить до 500 студентов.")
        if None in row or any(value is None for value in row.values()):
            errors.append(f"Строка {row_number}: неверное число столбцов.")
            continue
        data = {key: value.strip() for key, value in row.items()}
        data["is_active"] = True
        form = StudentForm(data)
        if data["number"] in numbers:
            errors.append(f"Строка {row_number}: номер повторяется в файле.")
        elif not form.is_valid():
            details = "; ".join(
                str(message)
                for messages in form.errors.values()
                for message in messages
            )
            errors.append(f"Строка {row_number}: {details}")
        else:
            records.append(data)
        numbers.add(data["number"])
    if errors:
        raise ValidationError(errors[:20])
    if not records:
        raise ValidationError("В файле нет студентов.")
    return records


@transaction.atomic
def import_students(records, group):
    count = 0
    for data in records:
        form = StudentForm(data)
        if not form.is_valid():
            raise ValidationError(
                f'Данные студента {data["number"]} уже изменились или такой номер существует. Загрузите файл заново.'
            )
        student = form.save()
        Enrollment.objects.create(
            student=student,
            group=group,
            started_on=student.admitted_at,
            note="Импорт списка студентов",
        )
        count += 1
    return count
