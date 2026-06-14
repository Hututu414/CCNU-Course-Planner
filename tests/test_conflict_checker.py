from src.conflict_checker import courses_conflict
from src.models import Course, Meeting


def make_course(name: str, meeting: Meeting) -> Course:
    return Course(
        source_sheet="测试",
        source_row=hash(name) % 10000,
        course_id=name,
        name=name,
        teacher="教师",
        credit=2.0,
        raw_time=meeting.raw,
        campus="本校",
        classroom="101",
        exam_type="考查",
        meetings=[meeting],
    )


def test_same_week_and_section_conflict():
    left = make_course("A", Meeting(1, 3, 4, 1, 17, "all"))
    right = make_course("B", Meeting(1, 4, 5, 1, 17, "all"))

    assert courses_conflict(left, right)


def test_different_weekday_not_conflict():
    left = make_course("A", Meeting(1, 3, 4, 1, 17, "all"))
    right = make_course("B", Meeting(2, 3, 4, 1, 17, "all"))

    assert not courses_conflict(left, right)


def test_odd_even_same_time_not_conflict():
    left = make_course("A", Meeting(1, 3, 4, 1, 17, "odd"))
    right = make_course("B", Meeting(1, 3, 4, 1, 17, "even"))

    assert not courses_conflict(left, right)


def test_all_week_and_odd_week_conflict():
    left = make_course("A", Meeting(1, 3, 4, 1, 17, "all"))
    right = make_course("B", Meeting(1, 3, 4, 1, 17, "odd"))

    assert courses_conflict(left, right)
