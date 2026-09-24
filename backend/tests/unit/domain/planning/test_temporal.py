from datetime import time
from app.domain.entities.planning.temporal import (
    DayOfWeek,
    TimeRange,
    DaySchedule,
    OpeningHoursSchedule,
    parse_opening_hours,
)


def test_time_range_can_accommodate():
    tr = TimeRange(start=time(8, 0), end=time(18, 0))
    assert tr.contains(time(11, 0)) is True
    assert tr.contains(time(7, 30)) is False
    assert tr.contains(time(18, 30)) is False

    # Within range with duration
    assert tr.can_accommodate(time(11, 0), 120) is True  # ends at 13:00 <= 18:00
    assert tr.can_accommodate(time(17, 0), 90) is False  # ends at 18:30 > 18:00


def test_parse_opening_hours_daily():
    sched = parse_opening_hours("Daily 08:00-18:00")
    assert sched.is_unknown is False
    assert sched.can_accommodate("Saturday", "11:00", 60) is True
    assert sched.can_accommodate("Saturday", "07:30", 60) is False
    assert sched.can_accommodate("Saturday", "17:30", 60) is False
    assert sched.can_accommodate("Monday", "11:00") is True


def test_parse_opening_hours_tue_sun():
    sched = parse_opening_hours("Tue-Sun 10:00-18:00")
    assert sched.is_unknown is False
    assert sched.can_accommodate("Monday", "11:00") is False  # Monday closed
    assert sched.can_accommodate("Saturday", "11:00") is True
    assert sched.can_accommodate("Sunday", "14:00") is True


def test_parse_opening_hours_split_shift():
    sched = parse_opening_hours("Tue-Sat 12:30-14:00 & 18:00-22:30")
    assert sched.is_unknown is False
    # Monday and Sunday closed
    assert sched.can_accommodate("Monday", "13:00") is False
    assert sched.can_accommodate("Sunday", "13:00") is False
    # Saturday lunch
    assert sched.can_accommodate("Saturday", "13:00", 60) is True
    # Saturday afternoon gap (between shifts)
    assert sched.can_accommodate("Saturday", "15:00", 60) is False
    # Saturday dinner
    assert sched.can_accommodate("Saturday", "19:00", 90) is True


def test_parse_opening_hours_24_hours():
    sched = parse_opening_hours("Daily 24 hours")
    assert sched.is_unknown is False
    assert sched.can_accommodate("Saturday", "03:00", 120) is True
    assert sched.can_accommodate("Sunday", "23:00", 60) is True


def test_parse_opening_hours_multi_clause():
    sched = parse_opening_hours("Mon-Sat 07:00-18:00, Sun 08:00-16:00")
    assert sched.is_unknown is False
    # Mon-Sat evening
    assert sched.can_accommodate("Saturday", "17:00", 30) is True
    assert sched.can_accommodate("Saturday", "19:00") is False
    # Sun earlier close
    assert sched.can_accommodate("Sunday", "15:00", 30) is True
    assert sched.can_accommodate("Sunday", "17:00") is False


def test_parse_opening_hours_unknown():
    sched = parse_opening_hours(None)
    assert sched.is_unknown is True
    assert sched.can_accommodate("Saturday", "11:00") is None  # Distinct from False!

    sched_empty = parse_opening_hours("")
    assert sched_empty.is_unknown is True
    assert sched_empty.can_accommodate("Saturday", "11:00") is None
