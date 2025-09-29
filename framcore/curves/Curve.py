"""Curve interface."""

from abc import ABC, abstractmethod

from numpy.typing import NDArray

from framcore import Base


class Curve(Base, ABC):
    """Curve interface class."""

    @abstractmethod
    def get_unique_name(self) -> str | None:
        """Return unique name of curve."""
        pass

    @abstractmethod
    def get_x_axis(self, is_float32: bool) -> NDArray:
        """
        Get array of x axis values.

        Args:
            is_float32 (bool): Flag for converting the array of values to numpy float32.

        Returns:
            NDArray: Numpy array of values.

        """
        pass

    @abstractmethod
    def get_y_axis(self, is_float32: bool) -> NDArray:
        """
        Get array of y axis values.

        Args:
            is_float32 (bool): Flag for converting the array of values to numpy float32.

        Returns:
            NDArray: Numpy array of values.

        """
        pass
