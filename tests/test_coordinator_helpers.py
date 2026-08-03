"""Tests for the pure helper functions in the coordinator module."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.tarif_edf.coordinator import (
    adjust_tempo_datetime,
    get_tempo_color_from_code,
    str_to_date,
    str_to_time,
    time_in_between,
)


def test_str_to_time():
    assert str_to_time("22:30") == datetime.strptime("22:30", "%H:%M").time()


def test_str_to_date():
    assert str_to_date("01/03/2026") == date(2026, 3, 1)


@pytest.mark.parametrize(
    ("now", "start", "end", "expected"),
    [
        ("10:00", "06:00", "22:00", True),
        ("23:00", "06:00", "22:00", False),
        ("23:00", "22:00", "06:00", True),  # crosses midnight
        ("02:00", "22:00", "06:00", True),
        ("12:00", "22:00", "06:00", False),
        ("22:00", "22:00", "06:00", True),  # inclusive start
        ("06:00", "22:00", "06:00", False),  # exclusive end
    ],
)
def test_time_in_between(now, start, end, expected):
    assert (
        time_in_between(str_to_time(now), str_to_time(start), str_to_time(end))
        is expected
    )


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (0, "indéterminé"),
        (1, "bleu"),
        (2, "blanc"),
        (3, "rouge"),
        (99, "indéterminé"),
    ],
)
def test_get_tempo_color_from_code(code, expected):
    assert get_tempo_color_from_code(code) == expected


def test_adjust_tempo_datetime():
    result = adjust_tempo_datetime(date(2026, 3, 1))
    assert result == datetime(2026, 3, 1, 6, 0, tzinfo=ZoneInfo("Europe/Paris"))
