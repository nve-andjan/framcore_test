from __future__ import annotations

import math
from datetime import datetime, timedelta, tzinfo

import numpy as np
from numpy.typing import NDArray

import framcore.expressions._time_vector_operations as v_ops
from framcore.fingerprints import Fingerprint
from framcore.timeindexes.TimeIndex import TimeIndex  # NB! full import path needed for inheritance to work
from framcore.timevectors import ReferencePeriod


class FixedFrequencyTimeIndex(TimeIndex):
    """TimeIndex with fixed frequency."""

    def __init__(
        self,
        start_time: datetime,
        period_duration: timedelta,
        num_periods: int,
        is_52_week_years: bool,
        extrapolate_first_point: bool,
        extrapolate_last_point: bool,
    ) -> None:
        """
        Initialize a FixedFrequencyTimeIndex.

        Parameters
        ----------
        start_time : datetime
            The starting datetime of the time index.
        period_duration : timedelta
            The duration of each period.
        num_periods : int
            The number of periods in the time index.
        is_52_week_years : bool
            Whether to use 52-week years.
        extrapolate_first_point : bool
            Whether to allow extrapolation of the first point.
        extrapolate_last_point : bool
            Whether to allow extrapolation of the last point.

        """
        if num_periods < 0:
            message = f"num_periods must be a positive integer. Got {num_periods}."
            raise ValueError(message)
        if period_duration < timedelta(seconds=1):
            message = f"period_duration must be at least one second. Got {period_duration}."
            raise ValueError(message)
        if not period_duration.total_seconds().is_integer():
            message = f"period_duration must be a whole number of seconds, got {period_duration.total_seconds()} s"
            raise ValueError(message)
        if is_52_week_years and start_time.isocalendar().week == 53:  #  original: assert start_time.isocalendar().week != 53  # noqa: PLR2004
            raise ValueError("Week of start_time must not be 53 when is_52_week_years is True.")
        self._check_type(num_periods, int)
        self._start_time = start_time
        self._period_duration = period_duration
        self._num_periods = num_periods
        self._is_52_week_years = is_52_week_years
        self._extrapolate_first_point = extrapolate_first_point
        self._extrapolate_last_point = extrapolate_last_point

    def __eq__(self, other) -> bool:  # noqa: ANN001
        """Check if equal to other."""
        if not isinstance(other, FixedFrequencyTimeIndex):
            return False
        return (
            self._start_time == other._start_time
            and self._period_duration == other._period_duration
            and self._num_periods == other._num_periods
            and self._is_52_week_years == other._is_52_week_years
            and self._extrapolate_first_point == other._extrapolate_first_point
            and self._extrapolate_last_point == other._extrapolate_last_point
        )

    def __hash__(self) -> int:
        """Return the hash value for the FixedFrequencyTimeIndex."""
        return hash(
            (
                self._start_time,
                self._period_duration,
                self._num_periods,
                self._is_52_week_years,
                self._extrapolate_first_point,
                self._extrapolate_last_point,
            ),
        )

    def __repr__(self) -> str:
        """Return a string representation of the FixedFrequencyTimeIndex."""
        return (
            f"FixedFrequencyTimeIndex("
            f"start_time={self._start_time}, "
            f"period_duration={self._period_duration}, "
            f"num_periods={self._num_periods}, "
            f"is_52_week_years={self._is_52_week_years}, "
            f"extrapolate_first_point={self._extrapolate_first_point}, "
            f"extrapolate_last_point={self._extrapolate_last_point})"
        )

    def get_fingerprint(self) -> Fingerprint:
        """Get the fingerprint."""
        return self.get_fingerprint_default()

    def get_timezone(self) -> tzinfo | None:
        """Get the timezone."""
        return self._start_time.tzinfo

    def get_start_time(self) -> datetime:
        """Get the start time."""
        return self._start_time

    def get_period_duration(self) -> timedelta:
        """Get the period duration."""
        return self._period_duration

    def get_num_periods(self) -> int:
        """Get the number of points."""
        return self._num_periods

    def is_constant(self) -> bool:
        """
        Return True if the time index is constant (single period and both extrapolation flags are True).

        Returns
        -------
        bool
            True if the time index is constant, False otherwise.

        """
        return self._num_periods == 1 and self._extrapolate_first_point == self._extrapolate_last_point is True

    def is_whole_years(self) -> bool:
        """Return True if index covers one or more full years."""
        start_time = self.get_start_time()
        start_year, start_week, start_weekday = start_time.isocalendar()
        if not start_week == start_weekday == 1:
            return False

        if not self.is_52_week_years():
            period_duration = self.get_period_duration()
            num_periods = self.get_num_periods()
            stop_time = start_time + num_periods * period_duration
            stop_year, stop_week, stop_weekday = stop_time.isocalendar()
            assert stop_year >= start_year
            return stop_week == stop_weekday == 1

        period_duration = self.get_period_duration()
        num_periods = self.get_num_periods()
        seconds_52_week_year = 52 * 168 * 3600
        num_years = (period_duration * num_periods).total_seconds() / seconds_52_week_year
        return num_years.is_integer()

    def get_reference_period(self) -> ReferencePeriod | None:
        """Get the reference period (only if is_whole_years() is True)."""
        if self.is_whole_years():
            start_year = self.get_start_time().isocalendar().year

            if self._is_52_week_years:
                num_years = (self.get_num_periods() * self.get_period_duration()) // timedelta(weeks=52)
            else:
                stop_year = self.get_stop_time().isocalendar().year
                num_years = stop_year - start_year
            return ReferencePeriod(start_year=start_year, num_years=num_years)
        return None

    def is_52_week_years(self) -> bool:
        """Return True if 52-week years and False if real ISO time."""
        return self._is_52_week_years

    def is_one_year(self) -> bool:
        """Return True if exactly one whole year."""
        start_time = self.get_start_time()
        start_year, start_week, start_weekday = start_time.isocalendar()
        if not start_week == start_weekday == 1:
            return False

        if not self.is_52_week_years():
            period_duration = self.get_period_duration()
            num_periods = self.get_num_periods()
            stop_time = start_time + num_periods * period_duration
            stop_year, stop_week, stop_weekday = stop_time.isocalendar()
            if not stop_week == stop_weekday == 1:
                return False
            return start_year + 1 == stop_year

        period_duration = self.get_period_duration()
        num_periods = self.get_num_periods()
        seconds_52_week_year = 52 * 168 * 3600
        num_years = (period_duration * num_periods).total_seconds() / seconds_52_week_year
        return num_years == 1.0

    def extrapolate_first_point(self) -> bool:
        """Return True if first value can be extrapolated backwards to fill missing values."""
        return self._extrapolate_first_point

    def extrapolate_last_point(self) -> bool:
        """Return True if last value can be extrapolated forward to fill missing values."""
        return self._extrapolate_last_point

    def get_period_average(self, vector: NDArray, start_time: datetime, duration: timedelta, is_52_week_years: bool) -> float:
        """Get the average over the period from the vector."""
        assert vector.shape == (self.get_num_periods(),)
        target_timeindex = FixedFrequencyTimeIndex(
            start_time=start_time,
            period_duration=duration,
            num_periods=1,
            is_52_week_years=is_52_week_years,
            extrapolate_first_point=self.extrapolate_first_point(),
            extrapolate_last_point=self.extrapolate_last_point(),
        )
        target_vector = np.zeros(1, dtype=vector.dtype)
        self.write_into_fixed_frequency(
            target_vector=target_vector,
            target_timeindex=target_timeindex,
            input_vector=vector,
        )
        return target_vector[0]

    def write_into_fixed_frequency(
        self,
        target_vector: NDArray,
        target_timeindex: FixedFrequencyTimeIndex,
        input_vector: NDArray,
    ) -> None:
        """
        Write the given input_vector into the target_vector according to the target_timeindex, applying necessary transformations.

        Parameters
        ----------
        target_vector : NDArray
            The array where the input_vector will be written to, modified in place.
        target_timeindex : FixedFrequencyTimeIndex
            The time index defining the fixed frequency structure for writing the input_vector into the target_vector.
        input_vector : NDArray
            The array containing the data to be written into the target_vector.

        Notes
        -----
        - If the object is constant (as determined by `self.is_constant()`), the input_vector is expected to have a single value,
          which will be used to fill the entire target_vector.
        - Otherwise, the method delegates the operation to `_write_into_fixed_frequency_recursive` for handling more complex cases.

        """
        if self.is_constant():
            assert input_vector.size == 1
            target_vector.fill(input_vector[0])
        else:
            self._write_into_fixed_frequency_recursive(target_vector, target_timeindex, input_vector)

    def _write_into_fixed_frequency_recursive(  # noqa: C901
        self,
        target_vector: NDArray,
        target_timeindex: FixedFrequencyTimeIndex,
        input_vector: NDArray,
        _depth: int = 0,  # only for recursion depth tracking
    ) -> None:
        """
        Recursively write the input_vector into the target_vector according to the target_timeindex, applying necessary transformations.

        Parameters
        ----------
        target_vector : NDArray
            The array where the input_vector will be written to, modified in place.
        target_timeindex : FixedFrequencyTimeIndex
            The time index defining the fixed frequency structure for writing the input_vector into the target_vector.
        input_vector : NDArray
            The array containing the data to be written into the target_vector.

        """
        if _depth > 100:  # noqa: PLR2004
            raise RecursionError("Maximum recursion depth (100) exceeded in _write_into_fixed_frequency_recursive.")

        if self == target_timeindex:
            np.copyto(target_vector, input_vector)
            return

        transformed_timeindex = None

        # Check differences between self and target_timeindex and apply transformations recursively
        if not target_timeindex._is_compatible_resolution(self):
            transformed_timeindex, transformed_vector = self._transform_to_compatible_resolution(input_vector, target_timeindex)

        elif target_timeindex.is_52_week_years() and not self.is_52_week_years():
            transformed_timeindex, transformed_vector = self._convert_to_52_week_years(input_vector=input_vector)

        elif not target_timeindex.is_52_week_years() and self.is_52_week_years():
            transformed_timeindex, transformed_vector = self._convert_to_iso_time(input_vector=input_vector)

        elif not self._is_same_period(target_timeindex):
            if self.is_one_year():
                transformed_timeindex, transformed_vector = self._repeat_oneyear(input_vector, target_timeindex)
            else:
                transformed_timeindex, transformed_vector = self._adjust_period(input_vector, target_timeindex)

        elif not self.is_same_resolution(target_timeindex):
            if target_timeindex.get_period_duration() < self._period_duration:
                v_ops.disaggregate(
                    input_vector=input_vector,
                    output_vector=target_vector,
                    is_disaggfunc_repeat=True,
                )
            else:
                v_ops.aggregate(
                    input_vector=input_vector,
                    output_vector=target_vector,
                    is_aggfunc_sum=False,
                )

        # Recursively write the transformed vector into the target vector
        if transformed_timeindex is not None:
            transformed_timeindex._write_into_fixed_frequency_recursive(  # noqa: SLF001
                target_vector=target_vector,
                target_timeindex=target_timeindex,
                input_vector=transformed_vector,
                _depth=_depth + 1,
            )

    def _convert_to_iso_time(self, input_vector: NDArray) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        """
        Convert the input vector to ISO time format.

        Parameters
        ----------
        input_vector : NDArray
            The input vector to be transformed into ISO time format.

        Returns
        -------
        tuple[FixedFrequencyTimeIndex, NDArray]
            A tuple containing the transformed FixedFrequencyTimeIndex and the transformed input vector.

        """
        transformed_vector = v_ops.convert_to_isotime(input_vector=input_vector, startdate=self._start_time, period_duration=self._period_duration)

        transformed_timeindex = self.copy_with(
            start_time=self._start_time,
            num_periods=transformed_vector.size,
            is_52_week_years=False,
        )

        return transformed_timeindex, transformed_vector

    def _convert_to_52_week_years(self, input_vector: NDArray) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        """
        Convert the input vector to a 52-week year format.

        This method adjusts the start time of the source index (if needed) and transforms the input vector to match the 52-week year format.

        Parameters
        ----------
        input_vector : NDArray
            The input vector to be transformed.
        startdate : datetime
            The start date of the input vector.
        period_duration : timedelta
            The duration of each period in the input vector.

        Returns
        -------
            tuple[FixedFrequencyTimeIndex, NDArray]
                A tuple containing the transformed FixedFrequencyTimeIndex and the transformed input vector.

        """
        adjusted_start_time, transformed_vector = v_ops.convert_to_modeltime(
            input_vector=input_vector,
            startdate=self._start_time,
            period_duration=self._period_duration,
        )
        transformed_timeindex = self.copy_with(
            start_time=adjusted_start_time,
            num_periods=transformed_vector.size,
            is_52_week_years=True,
        )

        return transformed_timeindex, transformed_vector

    def _is_compatible_resolution(self, other: FixedFrequencyTimeIndex) -> bool:
        """Check if the period duration and start time are compatible with another FixedFrequencyTimeIndex."""
        return self._is_compatible_period(other) and self._is_compatible_starttime(other)

    def _is_compatible_period(self, other: FixedFrequencyTimeIndex) -> bool:
        modulus = self._period_duration.total_seconds() % other.get_period_duration().total_seconds()
        return modulus == 0

    def _is_compatible_starttime(self, other: FixedFrequencyTimeIndex) -> bool:
        delta = abs(self._start_time - other.get_start_time()).total_seconds()
        modulus = delta % other._period_duration.total_seconds()
        return modulus == 0

    def _transform_to_compatible_resolution(
        self,
        input_vector: NDArray,
        target_timeindex: FixedFrequencyTimeIndex,
    ) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        """
        Transform the input vector and source time index to match the target time index resolution.

        Parameters
        ----------
        input_vector : NDArray
            The input vector to be transformed.
        target_timeindex : FixedFrequencyTimeIndex
            The target time index to match the resolution of.

        Returns
        -------
        tuple[FixedFrequencyTimeIndex, NDArray]
            A tuple containing the transformed FixedFrequencyTimeIndex and the transformed input vector.

        """
        new_period_duration = timedelta(
            seconds=math.gcd(
                int(self._period_duration.total_seconds()),
                int(target_timeindex.get_period_duration().total_seconds()),
                int((self._start_time - target_timeindex.get_start_time()).total_seconds()),
            ),
        )

        transformed_timeindex = self.copy_with(
            period_duration=new_period_duration,
            num_periods=int(self._period_duration.total_seconds() // new_period_duration.total_seconds()) * self._num_periods,
        )

        transformed_vector = np.zeros(transformed_timeindex.get_num_periods(), dtype=input_vector.dtype)
        v_ops.disaggregate(
            input_vector=input_vector,
            output_vector=transformed_vector,
            is_disaggfunc_repeat=True,
        )

        return transformed_timeindex, transformed_vector

    def _is_same_period(self, other: FixedFrequencyTimeIndex) -> bool:
        """Check if the start and stop times are the same."""
        return self._start_time == other.get_start_time() and self.get_stop_time() == other.get_stop_time()

    def is_same_resolution(self, other: FixedFrequencyTimeIndex) -> bool:
        """Check if the period duration is the same."""
        return self._period_duration == other.get_period_duration()

    def get_stop_time(self) -> datetime:
        """Get the stop time of the TimeIndex."""
        return self._start_time + self._period_duration * self._num_periods

    def slice(
        self,
        input_vector: NDArray,
        start_year: int,
        num_years: int,
        target_start_year: int,
        target_num_years: int,
    ) -> NDArray:
        """Periodize the input vector to match the target timeindex."""
        if self._is_52_week_years:
            return v_ops.periodize_modeltime(input_vector, start_year, num_years, target_start_year, target_num_years)
        return v_ops.periodize_isotime(input_vector, start_year, num_years, target_start_year, target_num_years)

    def _slice_start(self, input_vector: NDArray, target_index: FixedFrequencyTimeIndex) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        """
        Slice the input vector to match the target time index.

        This method handles slicing the input vector to fit the target time index,
        ensuring that the start time aligns correctly.
        """
        num_periods_to_slice = self._periods_between(
            self._start_time,
            target_index.get_start_time(),
            self._period_duration,
        )
        transformed_timeindex = self.copy_with(
            start_time=target_index.get_start_time(),
            num_periods=self._num_periods - num_periods_to_slice,
        )
        transformed_vector = input_vector[num_periods_to_slice:]

        return transformed_timeindex, transformed_vector

    def _slice_end(self, input_vector: NDArray, target_index: FixedFrequencyTimeIndex) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        """
        Slice the input vector to match the target time index.

        This method handles slicing the input vector to fit the target time index,
        ensuring that the stop time aligns correctly.
        """
        num_periods_to_slice = self._periods_between(
            self.get_stop_time(),
            target_index.get_stop_time(),
            self._period_duration,
        )
        transformed_timeindex = self.copy_with(num_periods=self._num_periods - num_periods_to_slice)
        transformed_vector = input_vector[:-num_periods_to_slice]

        return transformed_timeindex, transformed_vector

    def total_duration(self) -> timedelta:
        """Get the duration of the TimeIndex."""
        return self._period_duration * self._num_periods

    def _extend_start(
        self,
        input_vector: NDArray,
        target_timeindex: FixedFrequencyTimeIndex,
    ) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        """
        Extend the start of the input vector to match the target time index.

        This method handles extrapolation of the first point if allowed.
        """
        if not self._extrapolate_first_point:
            raise ValueError("Cannot extend start without extrapolation.")

        num_periods_to_extend = self._periods_between(self._start_time, target_timeindex.get_start_time(), self._period_duration)
        extended_vector = np.concatenate((np.full(num_periods_to_extend, input_vector[0]), input_vector))

        transformed_timeindex = self.copy_with(
            start_time=target_timeindex.get_start_time(),
            num_periods=self._num_periods + num_periods_to_extend,
        )

        return transformed_timeindex, extended_vector

    def _extend_end(
        self,
        input_vector: NDArray,
        target_timeindex: FixedFrequencyTimeIndex,
    ) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        if not self._extrapolate_last_point:
            raise ValueError("Cannot extend end without extrapolation.")

        num_periods_to_extend = self._periods_between(
            self.get_stop_time(),
            target_timeindex.get_stop_time(),
            self._period_duration,
        )
        extended_vector = np.concatenate((input_vector, np.full(num_periods_to_extend, input_vector[-1])))
        target_timeindex = self.copy_with(num_periods=self._num_periods + num_periods_to_extend)

        return target_timeindex, extended_vector

    def _repeat_oneyear(self, input_vector: NDArray, target_timeindex: FixedFrequencyTimeIndex) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        """
        Repeat the one-year time index.

        This method creates a new time vector by repeating the input vector over the time period defined by the target time index.

        Parameters
        ----------
        input_vector : NDArray
            The input vector to be repeated.
        target_timeindex : FixedFrequencyTimeIndex
            The target time index defining the start and duration of the target period.

        Returns
        -------
        tuple[FixedFrequencyTimeIndex, NDArray]
            A tuple containing the new FixedFrequencyTimeIndex and the transformed input vector.

        """
        if self.is_52_week_years():
            transformed_vector = self._repeat_one_year_modeltime(
                input_vector=input_vector,
                target_timeindex=target_timeindex,
            )
        else:
            transformed_vector = self._repeat_one_year_isotime(
                input_vector=input_vector,
                target_timeindex=target_timeindex,
            )
        transformed_timeindex = self.copy_with(
            start_time=target_timeindex.get_start_time(),
            num_periods=transformed_vector.size,
        )

        return transformed_timeindex, transformed_vector

    def _repeat_one_year_isotime(self, input_vector: NDArray, target_timeindex: FixedFrequencyTimeIndex) -> NDArray:
        """
        Repeat the one-year ISO time index.

        This method creates a new time vector by repeating the input vector over the time period defined by the target time index.

        Parameters
        ----------
        input_vector : NDArray
            The input vector to be repeated.
        target_timeindex : FixedFrequencyTimeIndex
            The target time index defining the start and stop times for the repetition.

        Returns
        -------
        NDArray
            The repeated vector that matches the target time index.

        """
        return v_ops.repeat_oneyear_isotime(
            input_vector=input_vector,
            input_start_date=self._start_time,
            period_duration=self.get_period_duration(),
            output_start_date=target_timeindex.get_start_time(),
            output_end_date=target_timeindex.get_stop_time(),
        )

    def _repeat_one_year_modeltime(self, input_vector: NDArray, target_timeindex: FixedFrequencyTimeIndex) -> NDArray:
        """
        Repeat the one-year model time index.

        This method creates a new time vector by repeating the input vector over the time period defined by the target time index.

        Parameters
        ----------
        input_vector : NDArray
            The input vector to be repeated.
        target_timeindex : FixedFrequencyTimeIndex
            The target time index defining the start and stop times for the repetition.

        Returns
        -------
        NDArray
            The repeated vector that matches the target time index.

        """
        return v_ops.repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=self._start_time,
            period_duration=self.get_period_duration(),
            output_start_date=target_timeindex.get_start_time(),
            output_end_date=target_timeindex.get_stop_time(),
        )

    def _adjust_period(self, input_vector: NDArray, target_timeindex: FixedFrequencyTimeIndex) -> tuple[FixedFrequencyTimeIndex, NDArray]:
        if target_timeindex.get_start_time() < self._start_time:
            if self._extrapolate_first_point:
                return self._extend_start(input_vector, target_timeindex)
            raise ValueError(
                (
                    "Cannot write into fixed frequency: incompatible time indices. "
                    "Start time of the target index is before the start time of the source index "
                    "and extrapolate_first_point is False."
                ),
            )
        if target_timeindex.get_stop_time() > self.get_stop_time():
            if self._extrapolate_last_point:
                return self._extend_end(input_vector, target_timeindex)
            raise ValueError(
                "Cannot write into fixed frequency: incompatible time indices. 'stop_time' of the target index is after the 'stop_time' of the source index and 'extrapolate_last_point' is False.",
            )
        if target_timeindex.get_start_time() > self.get_start_time():
            return self._slice_start(input_vector, target_timeindex)

        if target_timeindex.get_stop_time() < self.get_stop_time():
            return self._slice_end(input_vector, target_timeindex)
        return target_timeindex, input_vector

    def _periods_between(self, first_time: datetime, second_time: datetime, period_duration: timedelta) -> int:
        """
        Calculate the number of periods between two times.

        Parameters
        ----------
        first_time : datetime
            The first time point.
        second_time : datetime
            The second time point.
        period_duration : timedelta
            The duration of each period.

        Returns
        -------
        int
            The number of periods between the two times.

        """
        return abs(first_time - second_time) // period_duration

    def copy_with(
        self,
        start_time: datetime | None = None,
        period_duration: timedelta | None = None,
        num_periods: int | None = None,
        is_52_week_years: bool | None = None,
        extrapolate_first_point: bool | None = None,
        extrapolate_last_point: bool | None = None,
    ) -> FixedFrequencyTimeIndex:
        """
        Create a copy of the FixedFrequencyTimeIndex with the same attributes, allowing specific fields to be overridden.

        Parameters
        ----------
        start_time : datetime, optional
            Override for the start time.
        period_duration : timedelta, optional
            Override for the period duration.
        num_periods : int, optional
            Override for the number of periods.
        is_52_week_years : bool, optional
            Override for 52-week years flag.
        extrapolate_first_point : bool, optional
            Override for extrapolate first point flag.
        extrapolate_last_point : bool, optional
            Override for extrapolate last point flag.

        Returns
        -------
        FixedFrequencyTimeIndex
            A new instance with the updated attributes.

        """
        return FixedFrequencyTimeIndex(
            start_time=start_time if start_time is not None else self._start_time,
            period_duration=period_duration if period_duration is not None else self._period_duration,
            num_periods=num_periods if num_periods is not None else self._num_periods,
            is_52_week_years=is_52_week_years if is_52_week_years is not None else self._is_52_week_years,
            extrapolate_first_point=extrapolate_first_point if extrapolate_first_point is not None else self._extrapolate_first_point,
            extrapolate_last_point=extrapolate_last_point if extrapolate_last_point is not None else self._extrapolate_last_point,
        )

    def copy_as_reference_period(self, reference_period: ReferencePeriod) -> FixedFrequencyTimeIndex:
        """
        Create a copy of the FixedFrequencyTimeIndex with one period matching the given reference period.

        Parameters
        ----------
        reference_period : ReferencePeriod
            The reference period to match for the output.

        Returns
        -------
        FixedFrequencyTimeIndex
            A new instance with the updated attributes.

        """
        start_year = reference_period.get_start_year()
        num_years = reference_period.get_num_years()
        start_time = datetime.fromisocalendar(start_year, 1, 1)
        if self.is_52_week_years():
            period_duration = timedelta(weeks=52 * num_years)
        else:
            stop_time = datetime.fromisocalendar(start_year + num_years, 1, 1)
            period_duration = stop_time - start_time
        return self.copy_with(
            start_time=start_time,
            num_periods=1,
            period_duration=period_duration,
        )

    def get_datetime_list(self) -> list[datetime]:
        """Return list of datetime including stop time."""
        t = self.get_start_time()
        n = self.get_num_periods()
        d = self.get_period_duration()
        return [t + i * d for i in range(n + 1)]
