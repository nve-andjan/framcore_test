"""Classes defining APIs for Loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from numpy.typing import NDArray

from framcore import Base
from framcore.fingerprints import Fingerprint
from framcore.timeindexes import TimeIndex
from framcore.timevectors import ReferencePeriod


class Loader(Base, ABC):
    """Base Loader class defining common API and functionality for all Loaders."""

    def __init__(self) -> None:
        """Set up cache of ids contained in the source of the Loader."""
        self._content_ids: list[str] = None

    def __repr__(self) -> str:
        """
        Overwrite string representation.

        Returns:
            str: Object represented as string.

        """
        return f"{type(self).__name__}({vars(self)})"

    def __getstate__(self) -> dict:
        """
        Return current object state, clearing any cached data.

        Returns:
            dict: The object's state dictionary.

        """
        self._clear_cache()
        return self.__dict__

    @abstractmethod
    def _clear_cache(self) -> None:
        pass

    # TODO: Is this correct? Also figure out how sharing Loaders should be when copying model given filepaths and copied
    # database
    def __deepcopy__(self, memo: dict) -> Loader:
        """
        Overwrite deepcopy.

        This is done to enable sharing of loaders. Since a loader is connected to one source, caching can thus be shared
        between Models.

        Args:
            memo (dict): Required argument.

        Returns:
            Loader: Returns itself.

        """
        return self

    @abstractmethod
    def get_source(self) -> object:
        """
        Return Loader source.

        Returns:
            object: Whatever the Loader interacts with to retrieve data.

        """
        pass

    @abstractmethod
    def set_source(self, new_source: object) -> None:
        """
        Set the Loader source.

        Args:
            new_source (object): Whatever the Loader should interact with to retrieve data.

        """
        pass

    @abstractmethod
    def get_metadata(self, content_id: str) -> object:
        """
        Get metadata from the Loader source.

        The metadata could describe behavior of the data in source.

        Args:
            content_id (str): Id of some content.

        Returns:
            object: Metadata in some format only the specific Loader knows.

        """
        pass

    @abstractmethod
    def _get_ids(self) -> list[str]:
        """
        Return list of names which can be used to access specific data structures whithin source.

        Most likely the names of all time vectors or curves in The Loader's source.

        Returns:
            list[str]

        """
        pass

    def get_ids(self) -> list[str]:
        """
        Handle caching of ids existing in the loaders source.

        Returns:
            list[str]: List containing ids in Loader source.

        """
        if self._content_ids is None:
            self._content_ids = self._get_ids()
            seen = set()
            duplicates = []
            for content_id in self._content_ids:
                if content_id in seen:
                    duplicates.append(content_id)
                else:
                    seen.add(content_id)
            if duplicates:
                msg = f"Duplicate ID's found in {self.get_source()}: {duplicates}"
                raise ValueError(msg)

        return self._content_ids

    def _id_exsists(self, content_id: str) -> None:
        """
        Check if a given id exists in source.

        Args:
            content_id (str): Id of some content.

        Raises:
            KeyError: If content id does not exist.

        """
        existing_ids = self.get_ids()
        if content_id not in existing_ids:
            # __repr__ should be overwritten in subclasses to produce enough info in error message.
            msg = f"Could not find ID {content_id} in {self}. Existing IDs: {existing_ids}"
            raise KeyError(msg)


class TimeVectorLoader(Loader, ABC):
    """Loader API for retrieving time vector data from some source."""

    @abstractmethod
    def get_values(self, vector_id: str) -> NDArray:
        """
        Return the values of a time vector in the Loader source.

        Args:
            vector_id (str): ID of the vector.

        Returns:
            NDArray: Numpy array of all values.

        """
        pass

    @abstractmethod
    def get_index(self, vector_id: str) -> TimeIndex:
        """
        Return the index a time vector in the Loader source.

        Args:
            vector_id (str): ID of the vector.

        Returns:
            NDArray: TimeIndex object.

        """
        pass

    @abstractmethod
    def get_unit(self, vector_id: str) -> str:
        """
        Return unit of the values within a time vector in the loader source.

        Args:
            vector_id (str): ID of the vector.

        Returns:
            str: String with unit.

        """
        pass

    @abstractmethod
    def is_max_level(self, vector_id: str) -> bool | None:
        """
        Check if the given TimeVector is a level representing max Volume/Capacity/Price.

        Args:
            vector_id (str): ID of the vector.

        Returns:
            True - vector is a level representing max Volume/Capacity.
            False - vector is a level representing average Volume/Capacity over a given reference period.
            None - vector is not a level.

        """
        pass

    @abstractmethod
    def is_zero_one_profile(self, vector_id: str) -> bool | None:
        """
        Check if the given TimeVector is a profile with values between zero and one.

        Args:
            vector_id (str): ID of the vector.

        Returns:
            True - vector is a profile with values between zero and one.
            False - vector is a profile where the mean value is 1 given a reference period.
            None - vector is not a profile.

        """
        pass

    @abstractmethod
    def get_reference_period(self, vector_id: str) -> ReferencePeriod | None:
        """
        Get the reference period of a given vector.

        Args:
            vector_id (str): ID of the vector.

        Returns:
            ReferencePeriod - if the vector is a mean one profile or average level, a reference period must exist.
            None - No reference period if vector is max level, zero one profile or not a level or profile.

        """
        pass

    def get_fingerprint(self, vector_id: str) -> Fingerprint:
        """Return Loader Fingerprint for given vector id."""
        f = Fingerprint(self)
        f.add("unit", self.get_unit(vector_id))
        f.add("index", self.get_index(vector_id))
        f.add("values", self.get_values(vector_id))
        return f


class CurveLoader(Loader, ABC):
    """Loader API for retrieving curve data from some source."""

    @abstractmethod
    def get_y_axis(self, curve_id: str) -> NDArray:
        """
        Return the values of a Curves y axis in the Loader source.

        Args:
            curve_id (str): ID of the curve.

        Returns:
            NDArray: Numpy array of all values in the y axis.

        """
        pass

    @abstractmethod
    def get_x_axis(self, curve_id: str) -> NDArray:
        """
        Return the values of a Curves x axis in the Loader source.

        Args:
            curve_id (str): ID of the curve.

        Returns:
            NDArray: Numpy array of all values in the x axis.

        """
        pass

    @abstractmethod
    def get_x_unit(self, curve_id: str) -> str:
        """
        Return the unit of the x axis of a specific curve.

        Args:
            curve_id (str): ID of the curve.

        Returns:
            str: Unit of the curve's x axis.

        """
        pass

    @abstractmethod
    def get_y_unit(self, curve_id: str) -> str:
        """
        Return the unit of the y axis of a specific curve.

        Args:
            curve_id (str): ID of the curve.

        Returns:
            str: Unit of the curve's y axis.

        """
        pass


class FileLoader(Loader, ABC):
    """Define common functionality and API for Loaders connected to a file as source."""

    _SUPPORTED_SUFFIXES: ClassVar[list[str]] = []

    def __init__(self, source: Path | str, relative_loc: Path | str | None = None) -> None:
        """
        Check validity of input parameters.

        Args:
            source (Path | str): Full file path or the absolute part of a file path
            relative_loc (Optional[Union[Path, str]], optional): The relative part of a file path. Defaults to None.

        """
        super().__init__()
        self._source = source
        self._relative_loc = relative_loc

        self._check_type(source, (Path, str))
        if self._relative_loc is not None:
            self._check_type(self._relative_loc, (Path, str))
        self._check_path_exists(self.get_source())
        self._check_path_supported(self.get_source())

    def __repr__(self) -> str:
        """Overwrite __repr__ to get better info."""
        return f"{type(self).__name__}(source={self._source}, relative_loc={self._relative_loc})"

    def get_source(self) -> Path:
        """Combine absolute and relative file path (if relative is defined) to get full source."""
        if self._relative_loc is None:
            return Path(self._source)
        return Path(self._source) / self._relative_loc

    def set_source(self, new_source: Path, relative_loc: Path | str | None = None) -> None:
        """
        Set absolute and relative parts of filepath.

        Args:
            new_source (Path): New absolute part.
            relative_loc (Optional[Union[Path, str]], optional): New relative part. Defaults to None.

        """
        self._source = new_source
        self._relative_loc = relative_loc

    @classmethod
    def get_supported_suffixes(cls) -> list[str]:
        """
        Return list of supported file types.

        Returns:
            list: List of filetypes.

        """
        return cls._SUPPORTED_SUFFIXES

    def _check_path_exists(self, path: Path) -> None:
        """
        Check if a file path exists.

        Args:
            path (Path): Path to check.

        Raises:
            FileNotFoundError

        """
        if not path.exists():
            msg = f"""File {path} does not exist. Could not create {type(self)}."""
            raise FileNotFoundError(msg)

    def _check_path_supported(self, path: Path) -> None:
        """
        Check if a file is supported/readable by this FileLoader instance.

        Args:
            path (Path): Path to check.

        Raises:
            ValueError: If the file type is not defined as supported.

        """
        filetype = path.suffix
        if filetype not in self._SUPPORTED_SUFFIXES:
            msg = f"File type of {path}, {filetype} is not supported by {type(self)}. Supported filetypes: {self._SUPPORTED_SUFFIXES}"
            raise ValueError(msg)
