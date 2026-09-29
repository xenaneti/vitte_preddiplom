from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


def append_row(sheet, values):
    sheet.append(values)
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def excel_report(data, date_from, date_to):
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Сводка"
    append_row(summary, ["Посещаемость студентов", str(date_from), str(date_to)])
    append_row(
        summary,
        [
            "Группа",
            "Присутствия",
            "Опоздания",
            "Без причины",
            "Уважительные",
            "Всего",
            "Посещаемость, %",
        ],
    )
    for group in data["groups"]:
        append_row(
            summary,
            [
                group["name"],
                group["present"],
                group["late"],
                group["absent"],
                group["excused"],
                group["total"],
                group["percentage"],
            ],
        )
    total = data["totals"]
    append_row(
        summary,
        [
            "Итого",
            total["present"],
            total["late"],
            total["absent"],
            total["excused"],
            total["total"],
            total["percentage"],
        ],
    )
    append_row(summary, ["Незакрытых занятий", data["unfinished"]])
    append_row(
        summary, ["Доля присутствий и опозданий среди отметок по проведённым занятиям."]
    )
    details = workbook.create_sheet("Отметки")
    append_row(
        details,
        [
            "Дата",
            "Группа",
            "Студент",
            "Номер студента",
            "Дисциплина",
            "Преподаватель",
            "Отметка",
            "Опоздание, мин.",
            "Причина",
            "Комментарий",
        ],
    )
    marks = (
        data["marks"]
        .select_related(
            "student",
            "lesson__assignment__group",
            "lesson__assignment__discipline",
            "lesson__assignment__teacher__user",
            "reason",
        )
        .order_by("lesson__date", "lesson__starts_at", "student__last_name")
    )
    for mark in marks:
        assignment = mark.lesson.assignment
        append_row(
            details,
            [
                mark.lesson.date,
                assignment.group.code,
                str(mark.student),
                mark.student.number,
                assignment.discipline.name,
                str(assignment.teacher),
                mark.get_status_display(),
                mark.late_minutes,
                str(mark.reason) if mark.reason else "",
                mark.comment,
            ],
        )
    student_sheet = workbook.create_sheet("Студенты")
    discipline_sheet = workbook.create_sheet("Дисциплины")
    for sheet, rows in [
        (student_sheet, data.get("student_rows", [])),
        (discipline_sheet, data.get("discipline_rows", [])),
    ]:
        append_row(
            sheet,
            [
                "Студент" if sheet == student_sheet else "Дисциплина",
                "Присутствия",
                "Опоздания",
                "Без причины",
                "Уважительные",
                "Всего",
                "Посещаемость, %",
            ],
        )
        for row in rows:
            append_row(
                sheet,
                [
                    row["name"],
                    row["present"],
                    row["late"],
                    row["absent"],
                    row["excused"],
                    row["total"],
                    row["percentage"],
                ],
            )
    for sheet, header_row in [
        (summary, 2),
        (details, 1),
        (student_sheet, 1),
        (discipline_sheet, 1),
    ]:
        sheet.freeze_panes = f"A{header_row + 1}"
        sheet.auto_filter.ref = (
            f"A{header_row}:{sheet.cell(sheet.max_row, sheet.max_column).coordinate}"
        )
        for cell in sheet[header_row]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="315ACB")
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = min(
                45,
                max(18, max(len(str(cell.value or "")) for cell in column[:100]) + 2),
            )
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="attendance_{date_from}_{date_to}.xlsx"'
    )
    response["Cache-Control"] = "no-store"
    return response


def matrix_report(data, group, date_from, date_to):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Журнал группы"
    append_row(sheet, [f"Группа {group}", str(date_from), str(date_to)])
    headers = ["Студент", "Номер"]
    for lesson in data["columns"]:
        headers.append(
            f"{lesson.date:%d.%m}\n{lesson.starts_at:%H:%M}\n{lesson.assignment.discipline.code}"
        )
    headers.append("Посещаемость, %")
    append_row(sheet, headers)
    colors = {"П": "E7F4EB", "Н": "FDECEC", "О": "FFF3D6", "У": "E8EFFF"}
    for row in data["rows"]:
        append_row(
            sheet,
            [str(row["student"]), row["student"].number]
            + [cell["symbol"] for cell in row["cells"]]
            + [row["percentage"]],
        )
        for cell in sheet[sheet.max_row][2:-1]:
            cell.alignment = Alignment(horizontal="center")
            if cell.value in colors:
                cell.fill = PatternFill("solid", fgColor=colors[cell.value])
    sheet.freeze_panes = "C3"
    sheet.row_dimensions[2].height = 50
    for cell in sheet[2]:
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="315ACB")
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = 12
    sheet.column_dimensions["A"].width = 35
    sheet.column_dimensions["B"].width = 16
    sheet.column_dimensions[sheet.cell(2, sheet.max_column).column_letter].width = 20
    append_row(
        sheet,
        ["П — присутствовал; Н — отсутствовал; О — опоздал; У — уважительная причина."],
    )
    append_row(
        sheet,
        [
            "Точка — нет отметки; тире — не входил в группу. Процент — только по проведённым занятиям."
        ],
    )
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="group_journal_{date_from}_{date_to}.xlsx"'
    )
    response["Cache-Control"] = "no-store"
    return response
