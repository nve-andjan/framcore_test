import copy
import datetime as dt

import numpy as np
import pytest

from framcore.timeindexes import ConstantTimeIndex, FixedFrequencyTimeIndex, ModelYear, ProfileTimeIndex

# 1. Given 30 years of data in some resolution (weekly, timely) in ISO-time format as input, return some years of data in same resolution but 52-week format.
# base index represents whole years
# target_timeindex represents whole years
# exatrapolate_first_point is False
# extrapolate_last_point is False


def test_when_identical_base_and_target_time_indexes_should_return_vector_indentical_to_input_vector():
    base_index = FixedFrequencyTimeIndex(
        start_time=dt.datetime.fromisocalendar(1990, 1, 1),
        period_duration=dt.timedelta(weeks=52),
        num_periods=30,
        is_52_week_years=True,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_index = copy.deepcopy(base_index)
    target_vector = np.empty(30, dtype=np.float32)
    input_vector = np.arange(1, 31, dtype=np.float32)

    base_index.write_into_fixed_frequency(
        target_vector=target_vector,
        target_timeindex=target_index,
        input_vector=input_vector,
    )

    assert np.array_equal(target_vector, input_vector), "Target vector values should match input vector values."


def test_when_target_vector_is_52_week_years_and_base_index_is_iso_time_should_return_vector_with_52_week_years_data():
    base_index = FixedFrequencyTimeIndex(
        start_time=dt.datetime.fromisocalendar(2020, 1, 1),
        period_duration=dt.timedelta(weeks=1),
        num_periods=53,
        is_52_week_years=False,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_index = FixedFrequencyTimeIndex(
        start_time=dt.datetime.fromisocalendar(2020, 1, 1),
        period_duration=dt.timedelta(weeks=1),
        num_periods=52,
        is_52_week_years=True,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_vector = np.empty(52, dtype=np.float32)
    input_vector = np.arange(0, 53, dtype=np.float32)

    base_index.write_into_fixed_frequency(
        target_vector=target_vector,
        target_timeindex=target_index,
        input_vector=input_vector,
    )

    assert np.array_equal(target_vector, input_vector[:52]), (
        "Target vector should contain the first 52 values of the input vector."
    )


def test_when_target_vector_is_iso_time_and_base_index_is_52_week_years_should_return_vector_with_iso_time_data():
    base_index = FixedFrequencyTimeIndex(
        start_time=dt.datetime.fromisocalendar(2020, 1, 1),
        period_duration=dt.timedelta(weeks=1),
        num_periods=52,
        is_52_week_years=True,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_index = FixedFrequencyTimeIndex(
        start_time=dt.datetime.fromisocalendar(2020, 1, 1),
        period_duration=dt.timedelta(weeks=1),
        num_periods=53,
        is_52_week_years=False,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_vector = np.empty(53, dtype=np.float32)
    input_vector = np.arange(0, 52, dtype=np.float32)

    base_index.write_into_fixed_frequency(
        target_vector=target_vector,
        target_timeindex=target_index,
        input_vector=input_vector,
    )

    # The first 52 values should match the input vector, and the last value should be the same as the last value of the input vector.
    assert np.array_equal(target_vector[:52], input_vector), (
        "First 52 values of target vector should match input vector."
    )
    assert target_vector[52] == input_vector[-1], "Last value of target vector should match last value of input vector."

def test_when_input_time_index_coarser_resolution_then_target_time_index_should_dissagregate_to_target_index_resolution():
    base_index = FixedFrequencyTimeIndex(
        start_time= dt.date.fromisocalendar(2020, 1, 1),
        period_duration= dt.timedelta(weeks=1),
        num_periods=53,
        is_52_week_years=False,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_index = base_index.copy_with(period_duration=dt.timedelta(hours=1), num_periods=53 * 7 * 24)
    target_vector = np.empty(target_index.get_num_periods(), dtype=np.float32)
    input_vector = np.arange(0, base_index.get_num_periods(), dtype=np.float32)

    base_index.write_into_fixed_frequency(
        target_vector=target_vector,
        target_timeindex=target_index,
        input_vector=input_vector,
    )

    # The target vector should contain values repeated for each hour in the week from the input vector.
    expected_vector = np.repeat(input_vector, 7 * 24)
    assert np.array_equal(target_vector, expected_vector), "Target vector should contain repeated values for each hour in the week from the input vector."

def test_when_input_time_index_finer_resolution_then_target_time_index_should_aggregate_to_target_index_resolution():
    base_index = FixedFrequencyTimeIndex(
        start_time=dt.date.fromisocalendar(2020, 1, 1),
        period_duration=dt.timedelta(hours=1),
    num_periods=53 * 7 * 24,
        is_52_week_years=False,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_index = base_index.copy_with(period_duration=dt.timedelta(weeks=1), num_periods=53)
    target_vector = np.empty(target_index.get_num_periods(), dtype=np.float32)
    input_vector = np.arange(0, base_index.get_num_periods(), dtype=np.float32)

    base_index.write_into_fixed_frequency(
        target_vector=target_vector,
        target_timeindex=target_index,
        input_vector=input_vector,
    )

    # The target vector should contain mean of the input vector values for each week.
    expected_vector = np.array([np.mean(input_vector[i:i + 7 * 24]) for i in range(0, len(input_vector), 7 * 24)])
    assert np.array_equal(target_vector, expected_vector), "Target vector should contain mean values of input vector for each week."

def test_with_constant_time_index():
    index = ConstantTimeIndex()

    input_vector = np.array([1.0], dtype=np.float32)

    target_index = FixedFrequencyTimeIndex(
        start_time=dt.datetime.fromisocalendar(2025, 1, 1),
        period_duration=dt.timedelta(weeks=1),
        num_periods=52 * 2,
        is_52_week_years=True,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    target_vector = np.empty(target_index.get_num_periods(), dtype=np.float32)

    index.write_into_fixed_frequency(
        target_vector=target_vector,
        target_timeindex=target_index,
        input_vector=input_vector,
    )

    assert np.array_equal(target_vector, np.repeat(input_vector, target_index.get_num_periods())), (
        "Target vector should contain repeated values of input vector for each period in the target time index."
    )

def test_profile_time_index():
    index = ProfileTimeIndex(
        start_year=1991,
        num_years=3,
        period_duration=dt.timedelta(hours=2),
        is_52_week_years=False,
    )

    input_vector = np.full((52 + 52 + 53) * 7 * 12, 1.0, dtype=np.float32)

    target_index = ModelYear(1992)
    target_vector = np.zeros(1, dtype=np.float32)

    index.write_into_fixed_frequency(
        target_vector=target_vector,
        target_timeindex=target_index,
        input_vector=input_vector,
    )

    assert np.array_equal(target_vector, np.array([1.0])), (
        "Target vector should contain the mean value of the input vector for the specified year."
    )
