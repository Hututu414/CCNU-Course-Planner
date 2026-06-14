from __future__ import annotations

from .models import Course, Meeting, Slot
from .utils import course_key


def meeting_conflicts(left: Meeting, right: Meeting) -> bool:
    if left.weekday != right.weekday:
        return False
    if not _ranges_overlap(left.start_section, left.end_section, right.start_section, right.end_section):
        return False
    return bool(_active_weeks(left) & _active_weeks(right))


def courses_conflict(left: Course, right: Course) -> bool:
    if course_key(left) == course_key(right):
        return False
    if left.occupied_slots or right.occupied_slots:
        return bool(left.occupied_slots & right.occupied_slots)
    return any(meeting_conflicts(left_meeting, right_meeting) for left_meeting in left.meetings for right_meeting in right.meetings)


def conflicts_with_any(course: Course, selected: list[Course]) -> bool:
    return conflicts_with_slots(course, build_selected_slots(selected, excluded_keys={course_key(course)}))


def build_selected_slots(
    selected: list[Course],
    excluded_keys: set[tuple[str, int, str, str, str]] | None = None,
) -> set[Slot]:
    slots: set[Slot] = set()
    for course in selected:
        if excluded_keys and course_key(course) in excluded_keys:
            continue
        slots.update(course.occupied_slots)
    return slots


def build_selected_course_map(selected: list[Course]) -> dict[tuple[str, int, str, str, str], Course]:
    return {course_key(course): course for course in selected}


def conflicts_with_slots(
    course: Course,
    selected_slots: set[Slot],
    selected_by_key: dict[tuple[str, int, str, str, str], Course] | None = None,
) -> bool:
    if selected_by_key is not None and course_key(course) in selected_by_key:
        return False
    return bool(course.occupied_slots & selected_slots)


def find_conflict_pairs(courses: list[Course]) -> list[tuple[Course, Course]]:
    pairs: list[tuple[Course, Course]] = []
    for left_index, left in enumerate(courses):
        for right in courses[left_index + 1 :]:
            if courses_conflict(left, right):
                pairs.append((left, right))
    return pairs


def _ranges_overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return max(left_start, right_start) <= min(left_end, right_end)


def _active_weeks(meeting: Meeting) -> set[int]:
    weeks = set(range(meeting.week_start, meeting.week_end + 1))
    if meeting.parity == "odd":
        return {week for week in weeks if week % 2 == 1}
    if meeting.parity == "even":
        return {week for week in weeks if week % 2 == 0}
    return weeks
