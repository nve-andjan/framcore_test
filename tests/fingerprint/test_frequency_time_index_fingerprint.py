from datetime import datetime, timedelta

from framcore.timeindexes import FixedFrequencyTimeIndex


def fixed_frequency_time_index(replacements: dict[str, object] | None = None):
    """
    Create a FixedFrequencyTimeIndex with default values.

    Args:
        replacements (dict[str, object], optional): Dictionary of properties to override.
            Defaults to None.

    Returns:
        FixedFrequencyTimeIndex: A FixedFrequencyTimeIndex object with the specified properties.

    """
    props = {
        "start_time": datetime(2020, 1, 1),
        "period_duration": timedelta(hours=1),
        "num_periods": 3,
        "is_52_week_years": False,
        "extrapolate_first_point": False,
        "extrapolate_last_point": False,
    }

    if replacements is not None:
        props.update(replacements)

    return FixedFrequencyTimeIndex(
        start_time=props["start_time"],
        period_duration=props["period_duration"],
        num_periods=props["num_periods"],
        is_52_week_years=props["is_52_week_years"],
        extrapolate_first_point=props["extrapolate_first_point"],
        extrapolate_last_point=props["extrapolate_last_point"],
    )


def test_same_fixed_frequency_time_indexes_should_have_same_fingerprint():
    index1 = fixed_frequency_time_index()
    index2 = fixed_frequency_time_index()

    assert index1.get_fingerprint().get_hash() == index2.get_fingerprint().get_hash()


def test_fixed_frequency_time_indexes_with_different_start_time_should_have_different_fingerprints():
    index1 = fixed_frequency_time_index()
    index2 = fixed_frequency_time_index({"start_time": datetime(2021, 1, 1)})

    assert index1.get_fingerprint().get_hash() != index2.get_fingerprint().get_hash()


def test_fixed_frequency_time_indexes_with_different_step_duration_should_have_different_fingerprints():
    index1 = fixed_frequency_time_index()
    index2 = fixed_frequency_time_index({"period_duration": timedelta(hours=5)})

    assert index1.get_fingerprint().get_hash() != index2.get_fingerprint().get_hash()


def test_fixed_frequency_time_indexes_with_different_num_points_should_have_different_fingerprints():
    index1 = fixed_frequency_time_index()
    index2 = fixed_frequency_time_index({"num_periods": 5})

    assert index1.get_fingerprint().get_hash() != index2.get_fingerprint().get_hash()


def test_fixed_frequency_time_indexes_with_different_is_52_week_years_should_have_different_fingerprints():
    index1 = fixed_frequency_time_index()
    index2 = fixed_frequency_time_index({"is_52_week_years": True})

    assert index1.get_fingerprint().get_hash() != index2.get_fingerprint().get_hash()


def test_frequency_time_indexes_with_different_extrapolate_first_point_should_have_different_fingerprints():
    index1 = fixed_frequency_time_index()
    index2 = fixed_frequency_time_index({"extrapolate_first_point": True})

    assert index1.get_fingerprint().get_hash() != index2.get_fingerprint().get_hash()


def test_fixed_frequency_time_indexes_with_different_extrapolate_last_point_should_have_different_fingerprints():
    index1 = fixed_frequency_time_index()
    index2 = fixed_frequency_time_index({"extrapolate_last_point": True})

    assert index1.get_fingerprint().get_hash() != index2.get_fingerprint().get_hash()
