from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from framcore.curves import Curve
from framcore.fingerprints import Fingerprint

if TYPE_CHECKING:
    from framcore.loaders import CurveLoader


class LoadedCurve(Curve):
    """
    Represents a curve loaded from a CurveLoader.

    Attributes
    ----------
    _curve_id : str
        Identifier for the curve.
    _loader : CurveLoader
        Loader instance used to retrieve curve data.
    _reference_period : Any
        Reference period for the curve (currently not set).

    Methods
    -------
    get_unique_name()
        Returns the unique name of the curve.
    get_x_axis(precision=None)
        Returns the x-axis data.
    get_y_axis(precision=None)
        Returns the y-axis data.
    get_x_unit()
        Returns the unit for the x-axis.
    get_y_unit()
        Returns the unit for the y-axis.
    get_loader()
        Returns the loader instance.
    get_fingerprint()
        Returns the fingerprint of the curve.

    """

    def __init__(self, curve_id: str, loader: CurveLoader) -> None:
        """
        Initialize a LoadedCurve instance.

        Parameters
        ----------
        curve_id : str
            Identifier for the curve.
        loader : CurveLoader
            Loader instance used to retrieve curve data.

        """
        self._curve_id = curve_id
        self._loader = loader

        # TODO: get from loader
        self._reference_period = None

    def __repr__(self) -> str:
        """Return a string representation of the LoadedCurve instance."""
        return f"{type(self).__name__}(curve_id={self._curve_id},loader={self._loader},x_unit={self.get_x_unit()}),y_unit={self.get_y_unit()}),"

    def get_unique_name(self) -> str:
        """
        Return the unique name of the curve.

        Returns
        -------
        str
            The unique name for the curve.

        """
        return self._curve_id

    def get_x_axis(self, is_float32: bool) -> NDArray:
        """
        Get x axis values of the curve as a numpy array.

        Args:
            is_float32 (bool): Flag for converting the array of values to numpy float32.

        Returns:
            NDArray: Numpy array of x axis values.

        """
        x_axis = self._loader.get_x_axis(self._curve_id)
        if is_float32:
            x_axis = x_axis.astype(np.float32)
        return x_axis

    def get_y_axis(self, is_float32: bool) -> NDArray:
        """
        Get y axis values of the curve as a numpy array.

        Args:
            is_float32 (bool): Flag for converting the array of values to numpy float32.

        Returns:
            NDArray: Numpy array of y axis values.

        """
        y_axis = self._loader.get_y_axis(self._curve_id)
        if is_float32:
            y_axis = y_axis.astype(np.float32)
        return y_axis

    def get_x_unit(self) -> str:
        """
        Return the unit for the x-axis.

        Returns
        -------
        str
            The unit for the x-axis.

        """
        return self._loader.get_x_unit(self._curve_id)

    def get_y_unit(self) -> str:
        """
        Return the unit for the y-axis.

        Returns
        -------
        str
            The unit for the y-axis.

        """
        return self._loader.get_y_unit(self._curve_id)

    def get_loader(self) -> CurveLoader:
        """
        Return the loader instance used to retrieve curve data.

        Returns
        -------
        CurveLoader
            The loader instance associated with this curve.

        """
        return self._loader

    def get_fingerprint(self) -> Fingerprint:
        """
        Return the fingerprint of the curve.

        The method is not implemented yet.
        """
        raise NotImplementedError("Not implemented yet.")
