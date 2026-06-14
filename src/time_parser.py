from __future__ import annotations

import re

from .models import Meeting


DEFAULT_WEEK_START = 1
DEFAULT_WEEK_END = 20

WEEKDAY_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "日": 7,
    "天": 7,
}


def parse_meetings(raw_time: str) -> list[Meeting]:
    text = _normalize_time_text(raw_time)
    if not text:
        return []

    meetings: list[Meeting] = []
    for segment in _split_segments(text):
        weekday = _parse_weekday(segment)
        section_range = _parse_sections(segment)
        if weekday is None or section_range is None:
            continue

        week_ranges = _parse_week_ranges(segment)
        parity = _parse_parity(segment)
        for week_start, week_end in week_ranges:
            meeting = Meeting(
                weekday=weekday,
                start_section=section_range[0],
                end_section=section_range[1],
                week_start=week_start,
                week_end=week_end,
                parity=parity,
                raw=segment,
            )
            meetings.append(meeting)
    return meetings


def _normalize_time_text(raw_time: str) -> str:
    text = "" if raw_time is None else str(raw_time)
    replacements = {
        "，": ",",
        "、": ",",
        "；": ";",
        "（": "(",
        "）": ")",
        "｛": "{",
        "｝": "}",
        "－": "-",
        "—": "-",
        "–": "-",
        "至": "-",
        "~": "-",
        "～": "-",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", "", text)


def _split_segments(text: str) -> list[str]:
    parts = [part.strip() for part in text.split(";") if part.strip()]
    return parts or [text]


def _parse_weekday(segment: str) -> int | None:
    match = re.search(r"(?:周|星期|礼拜)([一二三四五六日天])", segment)
    if not match:
        return None
    return WEEKDAY_MAP.get(match.group(1))


def _parse_sections(segment: str) -> tuple[int, int] | None:
    match = re.search(r"第([0-9,\-]+)节", segment)
    if not match:
        return None

    numbers: list[int] = []
    for token in match.group(1).split(","):
        if not token:
            continue
        if "-" in token:
            start, end = _parse_range_token(token)
            numbers.extend(range(start, end + 1))
        elif token.isdigit():
            numbers.append(int(token))

    if not numbers:
        return None
    return min(numbers), max(numbers)


def _parse_week_ranges(segment: str) -> list[tuple[int, int]]:
    week_text = _extract_week_text(segment)
    if not week_text:
        return [(DEFAULT_WEEK_START, DEFAULT_WEEK_END)]

    cleaned = week_text.replace("第", "").replace("周", "")
    cleaned = cleaned.replace("单", "").replace("双", "").replace("全部", "")
    cleaned = cleaned.strip(",;(){}")
    if not cleaned:
        return [(DEFAULT_WEEK_START, DEFAULT_WEEK_END)]

    ranges: list[tuple[int, int]] = []
    for token in cleaned.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            ranges.append(_parse_range_token(token))
        elif token.isdigit():
            week = int(token)
            ranges.append((week, week))

    return ranges or [(DEFAULT_WEEK_START, DEFAULT_WEEK_END)]


def _extract_week_text(segment: str) -> str:
    brace_match = re.search(r"\{([^}]*)\}", segment)
    if brace_match:
        return brace_match.group(1)

    week_match = re.search(r"(第?[0-9,\-]+周|单周|双周)", segment)
    return week_match.group(1) if week_match else ""


def _parse_range_token(token: str) -> tuple[int, int]:
    left, right = token.split("-", 1)
    start, end = int(left), int(right)
    return (start, end) if start <= end else (end, start)


def _parse_parity(segment: str) -> str:
    if "单周" in segment or "(单)" in segment:
        return "odd"
    if "双周" in segment or "(双)" in segment:
        return "even"
    return "all"
