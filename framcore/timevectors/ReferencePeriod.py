from framcore import Base


class ReferencePeriod(Base):
    """ReferencePeriod class represents a period of one or more years."""

    def __init__(self, start_year: int, num_years: int) -> None:
        """Initialize a ReferencePeriod with the start year and number of years."""
        self._check_type(start_year, int)
        self._check_type(num_years, int)
        if start_year < 0:
            message = f"start_year must be a positive integer. Got {start_year}."
            raise ValueError(message)
        if num_years < 0:
            message = f"num_years must be a positive integer. Got {num_years}."
            raise ValueError(message)
        self._start_year = start_year
        self._num_years = num_years

    def get_start_year(self) -> int:
        """Get the start_year from a ReferencePeriod instance."""
        return self._start_year

    def get_num_years(self) -> int:
        """Get the number of years in the ReferencePeriod."""
        return self._num_years

    def __eq__(self, other) -> bool:  # noqa: ANN001
        """Check if self and other are equal."""
        if not isinstance(other, type(self)):
            return False
        return self._start_year == other._start_year and self._num_years == other._num_years

    def __hash__(self) -> int:
        """Compute hash value.."""
        return hash(
            (
                self._start_year,
                self._num_years,
            ),
        )
