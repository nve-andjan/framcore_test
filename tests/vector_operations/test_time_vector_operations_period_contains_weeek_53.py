from datetime import datetime

import pytest

from framcore.expressions._time_vector_operations import _period_contains_week_53


@pytest.mark.parametrize(("start", "end", "expected"), [
    (datetime(2020, 1, 1), datetime(2020, 12, 28), False),
    (datetime(2020, 1, 1), datetime(2020, 12, 29), True),
    (datetime(2020, 12, 27), datetime(2021, 1, 3), True),
    (datetime(2020, 12, 28), datetime(2021, 1, 3), True),
    (datetime(2020, 12, 27), datetime(2021, 1, 4), True),
    (datetime(2020, 12, 28), datetime(2021, 1, 4), True),
    (datetime(2021, 1, 3), datetime(2021, 1, 4), True),
    (datetime(2021, 1, 4), datetime(2021, 1, 10), False),
],
ids=[
    "2020-01-01 - 2020-12-28: False",
    "2020-01-01 - 2020-12-29: True",
    "2020-12-27 - 2021-01-03: True",
    "2020-12-28 - 2021-01-03: True",
    "2020-12-27 - 2021-01-04: True",
    "2020-12-28 - 2021-01-04: True",
    "2021-01-03 - 2021-01-04: True",
    "2021-01-04 - 2021-01-10: True",
])
def test_period_contains_week_53(start: datetime, end: datetime, expected: bool):
    assert _period_contains_week_53(start, end) is expected
