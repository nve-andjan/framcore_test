from datetime import datetime

import pytest

from framcore.expressions._time_vector_operations import _find_all_week_53_periods


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (
            datetime(2020, 1, 1),
            datetime(2020, 12, 28),
            [],
        ),
        (
            datetime(2020, 1, 1),
            datetime(2020, 12, 29),
            [(datetime(2020, 12, 28), datetime(2020, 12, 29))],
        ),
        (
            datetime(2020, 1, 1),
            datetime(2021, 1, 4),
            [(datetime(2020, 12, 28), datetime(2021, 1, 4))],
        ),
        (
            datetime(2020, 12, 27),
            datetime(2021, 1, 4),
            [(datetime(2020, 12, 28), datetime(2021, 1, 4))],
        ),
        (
            datetime(2020, 12, 28),
            datetime(2021, 1, 4),
            [(datetime(2020, 12, 28), datetime(2021, 1, 4))],
        ),
        (
            datetime(2020, 12, 29),
            datetime(2021, 1, 4),
            [(datetime(2020, 12, 29), datetime(2021, 1, 4))],
        ),
        (
            datetime(2020, 12, 29),
            datetime(2021, 1, 5),
            [(datetime(2020, 12, 29), datetime(2021, 1, 4))],
        ),
        (
            datetime(2021, 1, 3),
            datetime(2021, 1, 5),
            [(datetime(2021, 1, 3), datetime(2021, 1, 4))],
        ),
        (
            datetime(2021, 1, 4),
            datetime(2021, 1, 5),
            [],
        ),
        (
            datetime(2020, 1, 1),
            datetime(2027, 1, 3),
            [
                (datetime(2020, 12, 28), datetime(2021, 1, 4)),
                (datetime(2026, 12, 28), datetime(2027, 1, 3))],
        ),
    ],
)
def test_find_all_week_53_periods(start: datetime, end: datetime, expected: list[tuple[datetime, datetime]]):
    result = _find_all_week_53_periods(start, end)

    assert len(result) == len(expected)
    assert result == expected
