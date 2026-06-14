from dataclasses import dataclass, field


Slot = tuple[int, int, int]


@dataclass
class Meeting:
    weekday: int
    start_section: int
    end_section: int
    week_start: int
    week_end: int
    parity: str = "all"
    raw: str = ""


@dataclass
class Course:
    source_sheet: str
    source_row: int
    course_id: str
    name: str
    teacher: str
    credit: float | None
    raw_time: str
    campus: str
    classroom: str
    exam_type: str
    category: str = ""
    meetings: list[Meeting] = field(default_factory=list)
    parse_warning: str = ""
    search_text: str = field(default="", init=False, repr=False)
    occupied_slots: set[Slot] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        self.rebuild_indexes()

    def rebuild_indexes(self) -> None:
        self.search_text = _build_search_text(self)
        self.occupied_slots = _build_occupied_slots(self.meetings)


def _build_search_text(course: Course) -> str:
    parts = [
        course.course_id,
        course.name,
        course.teacher,
        course.raw_time,
        course.campus,
        course.classroom,
        course.exam_type,
        course.category,
        course.source_sheet,
    ]
    return " ".join(part for part in parts if part).casefold()


def _build_occupied_slots(meetings: list[Meeting]) -> set[Slot]:
    slots: set[Slot] = set()
    for meeting in meetings:
        for week in range(meeting.week_start, meeting.week_end + 1):
            if meeting.parity == "odd" and week % 2 == 0:
                continue
            if meeting.parity == "even" and week % 2 == 1:
                continue
            for section in range(meeting.start_section, meeting.end_section + 1):
                slots.add((meeting.weekday, week, section))
    return slots
