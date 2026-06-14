from src.time_parser import parse_meetings


def test_parse_basic_weekday_sections_and_weeks():
    meetings = parse_meetings("周一第3,4节{第1-17周}")

    assert len(meetings) == 1
    meeting = meetings[0]
    assert meeting.weekday == 1
    assert meeting.start_section == 3
    assert meeting.end_section == 4
    assert meeting.week_start == 1
    assert meeting.week_end == 17
    assert meeting.parity == "all"


def test_parse_three_consecutive_sections():
    meetings = parse_meetings("周五第9,10,11节{第1-17周}")

    assert len(meetings) == 1
    assert meetings[0].weekday == 5
    assert meetings[0].start_section == 9
    assert meetings[0].end_section == 11


def test_parse_multiple_segments():
    meetings = parse_meetings("周五第3,4节{第17-19周}(全部);周二第3,4节{第4-16周}(全部);")

    assert len(meetings) == 2
    assert {meeting.weekday for meeting in meetings} == {2, 5}


def test_parse_multiple_week_ranges():
    meetings = parse_meetings("周一第9,10节{第1-4,13-16周}(全部);")

    assert len(meetings) == 2
    assert (meetings[0].week_start, meetings[0].week_end) == (1, 4)
    assert (meetings[1].week_start, meetings[1].week_end) == (13, 16)
