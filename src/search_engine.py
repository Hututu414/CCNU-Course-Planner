from __future__ import annotations

from .conflict_checker import build_selected_course_map, build_selected_slots, conflicts_with_slots
from .models import Course
from .utils import course_search_text, normalize_search_text


def search_courses(
    courses: list[Course],
    query: str,
    hide_conflicts: bool,
    selected: list[Course],
    selected_slots: set[tuple[int, int, int]] | None = None,
    limit: int | None = None,
) -> list[Course]:
    keywords = [normalize_search_text(part) for part in query.split() if part.strip()]
    slots = selected_slots if selected_slots is not None else build_selected_slots(selected)
    selected_by_key = build_selected_course_map(selected)
    results: list[Course] = []
    for course in courses:
        if hide_conflicts and conflicts_with_slots(course, slots, selected_by_key=selected_by_key):
            continue
        text = course_search_text(course)
        if all(keyword in text for keyword in keywords):
            results.append(course)
            if limit is not None and len(results) >= limit:
                break
    return results
