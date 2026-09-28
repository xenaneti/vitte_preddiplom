from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


def append_row(sheet, values):
    sheet.append(values)
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = 's'


def excel_report(data, date_from, date_to):
    workbook = Workbook()
    summary = workbook.active
    summary.title = 'Сводка'
    append_row(summary, ['Посещаемость студентов', str(date_from), str(date_to)])
    append_row(summary, ['Группа', 'Присутствия', 'Опоздания', 'Без причины', 'Уважительные', 'Всего', 'Посещаемость, %'])
    for group in data['groups']:
        append_row(summary, [group['name'], group['present'], group['late'], group['absent'], group['excused'], group['total'], group['percentage']])
    total = data['totals']
    append_row(summary, ['Итого', total['present'], total['late'], total['absent'], total['excused'], total['total'], total['percentage']])
    append_row(summary, ['Незакрытых занятий', data['unfinished']])
    append_row(summary, ['Доля присутствий и опозданий среди отметок по проведённым занятиям.'])
    details = workbook.create_sheet('Отметки')
    append_row(details, ['Дата', 'Группа', 'Студент', 'Номер студента', 'Дисциплина', 'Преподаватель', 'Отметка', 'Опоздание, мин.', 'Причина', 'Комментарий'])
    marks = data['marks'].select_related('student', 'lesson__assignment__group', 'lesson__assignment__discipline', 'lesson__assignment__teacher__user', 'reason').order_by('lesson__date', 'lesson__starts_at', 'student__last_name')
    for mark in marks:
        assignment = mark.lesson.assignment
        append_row(details, [mark.lesson.date, assignment.group.code, str(mark.student), mark.student.number, assignment.discipline.name, str(assignment.teacher), mark.get_status_display(), mark.late_minutes, str(mark.reason) if mark.reason else '', mark.comment])
    for sheet, header_row in [(summary, 2), (details, 1)]:
        sheet.freeze_panes = f'A{header_row + 1}'
        sheet.auto_filter.ref = f'A{header_row}:{sheet.cell(sheet.max_row, sheet.max_column).coordinate}'
        for cell in sheet[header_row]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='315ACB')
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = min(45, max(18, max(len(str(cell.value or '')) for cell in column[:100]) + 2))
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="attendance_{date_from}_{date_to}.xlsx"'
    response['Cache-Control'] = 'no-store'
    return response
