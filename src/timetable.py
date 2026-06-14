from __future__ import annotations

import hashlib

from .conflict_checker import find_conflict_pairs
from .models import Course, Meeting
from .utils import course_key, shorten_text


WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MAX_SECTION = 12
COURSE_COLORS = [
    ("#e8f3ff", "#0f4c81"),
    ("#eaf7ef", "#17633a"),
    ("#fff3d6", "#8a5a00"),
    ("#f1edff", "#55369b"),
    ("#e8faf9", "#0f6f6a"),
    ("#fff0f0", "#9f1239"),
    ("#edf7d7", "#4d6500"),
    ("#f4eefb", "#6b2d83"),
    ("#eaf0ff", "#244c9a"),
    ("#fff0e5", "#9a4b00"),
]


def format_meeting(meeting: Meeting) -> str:
    parity_text = {"all": "", "odd": " 单周", "even": " 双周"}.get(meeting.parity, "")
    return f"{meeting.week_start}-{meeting.week_end}周{parity_text}".strip()


def course_cell_text(course: Course, meeting: Meeting) -> str:
    details = [
        course.name,
        course.teacher,
        course.classroom,
        format_meeting(meeting),
        course.campus,
    ]
    return "\n".join(part for part in details if part)


def stable_course_colors(course: Course) -> tuple[str, str]:
    digest = hashlib.sha1("|".join(map(str, course_key(course))).encode("utf-8")).digest()
    return COURSE_COLORS[digest[0] % len(COURSE_COLORS)]


def build_timetable_cell_entries(selected: list[Course], max_section: int = MAX_SECTION) -> list[list[list[dict]]]:
    conflict_keys = _conflicting_course_keys(selected)
    grid: list[list[list[dict]]] = [[[] for _ in range(7)] for _ in range(max_section)]
    for course in selected:
        background, foreground = stable_course_colors(course)
        is_conflict = course_key(course) in conflict_keys
        for meeting in course.meetings:
            if meeting.weekday < 1 or meeting.weekday > 7:
                continue
            start = max(1, meeting.start_section)
            end = min(max_section, meeting.end_section)
            for section in range(start, end + 1):
                grid[section - 1][meeting.weekday - 1].append(
                    {
                        "course": course,
                        "meeting": meeting,
                        "title": shorten_text(course.name, 14),
                        "details": " / ".join(
                            part
                            for part in [
                                shorten_text(course.teacher, 10),
                                shorten_text(course.classroom, 10),
                                format_meeting(meeting),
                                shorten_text(course.campus, 8),
                            ]
                            if part
                        ),
                        "full_text": course_cell_text(course, meeting),
                        "background": background,
                        "foreground": foreground,
                        "conflict": is_conflict,
                    }
                )
    return grid


def build_timetable_grid(selected: list[Course], max_section: int = MAX_SECTION) -> list[list[str]]:
    grid: list[list[list[str]]] = [[[] for _ in range(7)] for _ in range(max_section)]
    for course in selected:
        for meeting in course.meetings:
            if meeting.weekday < 1 or meeting.weekday > 7:
                continue
            start = max(1, meeting.start_section)
            end = min(max_section, meeting.end_section)
            for section in range(start, end + 1):
                grid[section - 1][meeting.weekday - 1].append(course_cell_text(course, meeting))

    return [["\n\n".join(cell) for cell in row] for row in grid]


def build_timetable_rows(selected: list[Course], max_section: int = MAX_SECTION) -> list[dict[str, str]]:
    grid = build_timetable_grid(selected, max_section=max_section)
    rows: list[dict[str, str]] = []
    for index, row in enumerate(grid, start=1):
        record = {"节次": f"第{index}节"}
        for weekday_index, label in enumerate(WEEKDAY_LABELS):
            record[label] = row[weekday_index]
        rows.append(record)
    return rows


def selected_conflict_summary(selected: list[Course]) -> list[str]:
    return [
        f"{left.name}（{left.teacher}） 与 {right.name}（{right.teacher}）"
        for left, right in find_conflict_pairs(selected)
    ]


def _conflicting_course_keys(selected: list[Course]) -> set[tuple[str, int, str, str, str]]:
    keys: set[tuple[str, int, str, str, str]] = set()
    for left, right in find_conflict_pairs(selected):
        keys.add(course_key(left))
        keys.add(course_key(right))
    return keys
