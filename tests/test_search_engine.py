from src.models import Course, Meeting
from src.search_engine import search_courses


def make_course(name: str, teacher: str, raw_time: str, weekday: int, section: int, campus: str = "本校") -> Course:
    return Course(
        source_sheet="测试",
        source_row=section,
        course_id=f"C{section}",
        name=name,
        teacher=teacher,
        credit=2.0,
        raw_time=raw_time,
        campus=campus,
        classroom="101",
        exam_type="考查",
        category="专业课",
        meetings=[Meeting(weekday, section, section + 1, 1, 17, "all", raw_time)],
    )


def test_single_keyword_search():
    courses = [
        make_course("数据库系统", "张三", "周一第1,2节{第1-17周}", 1, 1),
        make_course("概率论", "李四", "周二第1,2节{第1-17周}", 2, 1),
    ]

    results = search_courses(courses, "数据库", False, [])

    assert [course.name for course in results] == ["数据库系统"]


def test_multi_keyword_search():
    courses = [
        make_course("大学体育", "王五", "周四第3,4节{第1-17周}", 4, 3, campus="南湖"),
        make_course("大学体育", "赵六", "周三第3,4节{第1-17周}", 3, 3, campus="本校"),
    ]

    results = search_courses(courses, "周四 体育 南湖", False, [])

    assert len(results) == 1
    assert results[0].teacher == "王五"


def test_hide_conflicts():
    selected = [make_course("已选课程", "教师", "周一第1,2节{第1-17周}", 1, 1)]
    conflict = make_course("冲突课程", "教师", "周一第2,3节{第1-17周}", 1, 2)
    available = make_course("可选课程", "教师", "周二第1,2节{第1-17周}", 2, 1)

    results = search_courses([conflict, available], "", True, selected)

    assert [course.name for course in results] == ["可选课程"]
