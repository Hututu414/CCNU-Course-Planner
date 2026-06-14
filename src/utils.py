from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Course


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLASS_TABLE_DIR = PROJECT_ROOT / "class_table"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        # Excel sometimes loads numeric identifiers as floats.
        number_part = text[:-2]
        if number_part.isdigit():
            return number_part
    return " ".join(text.split())


def normalize_header(value: Any) -> str:
    return clean_text(value).replace(" ", "").replace("\n", "").replace("\r", "")


def normalize_search_text(value: str) -> str:
    return clean_text(value).casefold()


def shorten_text(value: str, max_chars: int) -> str:
    text = clean_text(value)
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 1)] + "…"


def course_key(course: Course) -> tuple[str, int, str, str, str]:
    return (
        course.source_sheet,
        course.source_row,
        course.course_id,
        course.name,
        course.teacher,
    )


def course_search_text(course: Course) -> str:
    if not course.search_text:
        course.rebuild_indexes()
    return course.search_text


def parse_float(value: Any) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def find_default_excel_path(class_table_dir: Path | None = None) -> Path | None:
    directory = class_table_dir or DEFAULT_CLASS_TABLE_DIR
    if not directory.exists():
        return None
    files = [p for p in directory.glob("*.xlsx") if not p.name.startswith("~$")]
    if not files:
        return None
    preferred = [p for p in files if "选课手册" in p.name]
    return sorted(preferred or files, key=lambda p: p.name)[0]
