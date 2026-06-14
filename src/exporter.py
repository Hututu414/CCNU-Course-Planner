from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment

from .models import Course
from .timetable import build_timetable_rows, format_meeting


def export_selected_courses(selected: list[Course], export_dir: str) -> str:
    directory = Path(export_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "selected_timetable.xlsx"

    selected_rows = [
        {
            "课程名称": course.name,
            "教师": course.teacher,
            "学分": course.credit,
            "原始上课时间": course.raw_time,
            "校区": course.campus,
            "教室": course.classroom,
            "考核方式": course.exam_type,
            "课程类别": course.category,
            "解析警告": course.parse_warning,
            "来源工作表": course.source_sheet,
            "来源行号": course.source_row,
        }
        for course in selected
    ]

    meeting_rows = []
    for course in selected:
        if not course.meetings:
            meeting_rows.append(
                {
                    "课程名称": course.name,
                    "星期": "",
                    "开始节次": "",
                    "结束节次": "",
                    "开始周": "",
                    "结束周": "",
                    "单双周": "",
                    "原始上课时间": course.raw_time,
                    "解析警告": course.parse_warning,
                }
            )
            continue
        for meeting in course.meetings:
            meeting_rows.append(
                {
                    "课程名称": course.name,
                    "星期": meeting.weekday,
                    "开始节次": meeting.start_section,
                    "结束节次": meeting.end_section,
                    "开始周": meeting.week_start,
                    "结束周": meeting.week_end,
                    "单双周": meeting.parity,
                    "周次文本": format_meeting(meeting),
                    "原始上课时间": course.raw_time,
                }
            )

    timetable_rows = build_timetable_rows(selected)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(selected_rows).to_excel(writer, sheet_name="已选课程", index=False)
        pd.DataFrame(meeting_rows).to_excel(writer, sheet_name="解析结果", index=False)
        pd.DataFrame(timetable_rows).to_excel(writer, sheet_name="可视化课表", index=False)
        _format_workbook(writer.book)

    return str(path)


def _format_workbook(workbook) -> None:
    for worksheet in workbook.worksheets:
        for column_cells in worksheet.columns:
            max_length = 8
            column_letter = column_cells[0].column_letter
            for cell in column_cells:
                value = "" if cell.value is None else str(cell.value)
                max_length = min(max(max_length, len(value)), 40)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            worksheet.column_dimensions[column_letter].width = max_length + 2
