"""Definition of SolverConfig interface."""

from __future__ import annotations

from abc import ABC
from pathlib import Path

from framcore import Base
from framcore.expressions import is_convertable
from framcore.timeindexes import TimeIndex


class SolverConfig(Base, ABC):
    """SolverConfig inteface class."""

    _SIMULATION_MODE_SERIAL = "serial"
    _SIMULATION_MODE_FORECAST = "forecast"

    _DIFF_POLICY_ERROR = "error"
    _DIFF_POLICY_IGNORE = "ignore"
    _DIFF_POLICY_BACKUP = "backup"

    def __init__(self) -> None:
        """Create internal variables with default values."""
        self._simulation_mode: str | None = None
        self._diff_policy: str = self._DIFF_POLICY_ERROR
        self._show_screen_output: bool = False
        self._currency: str | None = None
        self._num_cpu_cores: int = 1
        self._is_float32 = True
        self._first_weather_year: int | None = None
        self._num_weather_years: int | None = None
        self._first_simulation_year: int | None = None
        self._num_simulation_years: int | None = None
        self._data_period: TimeIndex | None = None
        self._commodity_unit_flow_default: str | None = None
        self._commodity_unit_stock_default: str | None = None
        self._commodity_unit_flows: dict[str, str] = {}
        self._commodity_unit_stocks: dict[str, str] = {}
        self._solve_folder: Path | None = None

    def set_solve_folder(self, folder: Path | str | None) -> None:
        """Set folder where solve related files will be written."""
        self._check_type(folder, (str, Path, type(None)))
        if isinstance(folder, str):
            folder = Path(folder)
        self._solve_folder = folder

    def get_solve_folder(self) -> Path | None:
        """Get folder where solve related files will be written."""
        return self._solve_folder

    def set_commodity_units(
        self,
        commodity: str,
        stock_unit: str,
        flow_unit: str | None = None,
        is_default: bool | None = None,
    ) -> None:
        """
        Set the stock and flow units for a commodity.

        Parameters
        ----------
        commodity : str
            The name of the commodity.
        stock_unit : str
            The unit for the commodity stock.
        flow_unit : str or None, optional
            The unit for the commodity flow, representing the rate of change of the stock unit over time.
        is_default : bool or None, optional
            If True, set these units as the default for all commodities.

        Raises
        ------
        ValueError
            If the flow unit is incompatible with the stock unit.

        """
        self._check_type(commodity, str)
        self._check_type(stock_unit, str)
        self._check_type(flow_unit, (str, type(None)))
        self._check_type(is_default, (bool, type(None)))
        if flow_unit:
            candidate = f"{stock_unit}/s"
            if not is_convertable(candidate, flow_unit):
                message = (
                    f"Incompatible units for commodity '{commodity}': stock_unit '{stock_unit}' flow_unit '{flow_unit}'"
                    "The flow_unit must represent the rate of change of the stock_unit over time."
                )
                raise ValueError(message)
        if is_default:
            self._warn_if_changed_defaults(stock_unit, flow_unit)
            self._commodity_unit_stock_default = stock_unit
            if flow_unit:
                self._commodity_unit_flow_default = flow_unit
        else:
            self._commodity_unit_stocks[commodity] = stock_unit
            self._commodity_unit_flows[commodity] = flow_unit

    def get_unit_stock(self, commodity: str) -> str:
        """
        Get the stock unit for a given commodity.

        Parameters
        ----------
        commodity : str
            The name of the commodity.

        Returns
        -------
        str
            The stock unit for the commodity.

        Raises
        ------
        ValueError
            If no stock unit is set for the commodity.

        """
        if commodity not in self._commodity_unit_stocks and not self._commodity_unit_stock_default:
            message = f"No stock unit set for '{commodity}'."
            raise ValueError(message)
        return self._commodity_unit_stocks.get(commodity, self._commodity_unit_stock_default)

    def get_unit_flow(self, commodity: str) -> str | None:
        """
        Get the flow unit for a given commodity.

        Parameters
        ----------
        commodity : str
            The name of the commodity.

        Returns
        -------
        str or None
            The flow unit for the commodity, or None if not set.

        """
        return self._commodity_unit_flows.get(commodity, self._commodity_unit_flow_default)

    def _warn_if_changed_defaults(self, stock_unit: str, flow_unit: str) -> None:
        if self._commodity_unit_flow_default and flow_unit != self._commodity_unit_flow_default:
            message = f"Replacing flow default from {self._commodity_unit_flow_default} to {flow_unit}. Usually default is only set once."
            self.send_warning_event(message)
        if self._commodity_unit_stock_default and stock_unit != self._commodity_unit_stock_default:
            message = f"Replacing stock default from {self._commodity_unit_stock_default} to {stock_unit}. Usually default is only set once."
            self.send_warning_event(message)

    def get_num_cpu_cores(self) -> int:
        """Return number of cpu cores JulES can use."""
        return self._num_cpu_cores

    def set_num_cpu_cores(self, n: int) -> int:
        """Set number of cpu cores JulES can use."""
        self._num_cpu_cores = n

    def set_currency(self, currency: str) -> None:
        """Set currency."""
        self._check_type(currency, str)
        self._currency = currency

    def get_currency(self) -> str | None:
        """Get currency."""
        return self._currency

    def set_screen_output_on(self) -> None:
        """Print output from JulES to stdout and logfile."""
        self._show_screen_output = True

    def set_screen_output_off(self) -> None:
        """Only print output from JulES to logfile."""
        self._show_screen_output = False

    def show_screen_output(self) -> bool:
        """Return True if screen output is set to be shown."""
        return self._show_screen_output

    def set_diff_policy_error(self) -> None:
        """Error if non-empty diff during solve."""
        self._diff_policy = self._DIFF_POLICY_ERROR

    def set_diff_policy_ignore(self) -> None:
        """Ignore if non-empty diff during solve."""
        self._diff_policy = self._DIFF_POLICY_IGNORE

    def set_diff_policy_backup(self) -> None:
        """Copy existing folder to folder/backup_[timestamp] folder if non-empty diff during solve."""
        self._diff_policy = self._DIFF_POLICY_BACKUP

    def is_diff_policy_error(self) -> bool:
        """Return True if error diff policy."""
        return self._diff_policy == self._DIFF_POLICY_ERROR

    def is_diff_policy_ignore(self) -> bool:
        """Return True if ignore diff policy."""
        return self._diff_policy == self._DIFF_POLICY_IGNORE

    def is_diff_policy_backup(self) -> bool:
        """Return True if backup diff policy."""
        return self._diff_policy == self._DIFF_POLICY_BACKUP

    def set_simulation_mode_serial(self) -> None:
        """Activate serial simulation mode."""
        self._simulation_mode = self._SIMULATION_MODE_SERIAL

    def is_simulation_mode_serial(self) -> bool:
        """Return True if serial simulation mode."""
        return self._simulation_mode == self._SIMULATION_MODE_SERIAL

    def set_data_period(self, period: TimeIndex) -> None:
        """Set period used in level value queries."""
        self._check_type(period, TimeIndex)
        self._data_period = period

    def get_data_period(self) -> TimeIndex | None:
        """Get period used in level value queries."""
        return self._data_period

    def set_simulation_years(self, first_year: int, num_years: int) -> None:
        """Set subset of scenario years. For serial simulation."""
        self._check_type(first_year, int)
        self._check_type(num_years, int)
        self._check_int(first_year, lower_bound=0, upper_bound=None)
        self._check_int(num_years, lower_bound=1, upper_bound=None)
        self._first_simulation_year = first_year
        self._num_simulation_years = num_years

    def get_simulation_years(self) -> tuple[int, int]:
        """
        Get simulation years (first_year, num_years).

        Return weather years as fallback if serial simulation.
        """
        if (self._first_simulation_year is None or self._num_simulation_years is None) and self.is_simulation_mode_serial():
            first_weather_year, num_weather_years = self.get_weather_years()
            if first_weather_year is not None and num_weather_years is not None:
                return first_weather_year, num_weather_years

        if self._first_simulation_year is None or self._num_simulation_years is None:
            message = "Simulation years not set."
            raise ValueError(message)
        return (self._first_simulation_year, self._num_simulation_years)

    def set_weather_years(self, first_year: int, num_years: int) -> None:
        """Set weather scenario period used in profiles."""
        self._check_type(first_year, int)
        self._check_type(num_years, int)
        self._check_int(first_year, lower_bound=0, upper_bound=None)
        self._check_int(num_years, lower_bound=1, upper_bound=None)
        self._first_weather_year = first_year
        self._num_weather_years = num_years

    def get_weather_years(self) -> tuple[int, int]:
        """Get weather scenario period (first_year, num_years) used in profiles."""
        if self._first_weather_year < 0 or self._num_weather_years < 0:
            message = "Scenario years not set."
            raise ValueError(message)
        return (self._first_weather_year, self._num_weather_years)

    def use_float32(self) -> None:
        """Use single precision floating point numbers in data management."""
        self._is_float32 = True

    def use_float64(self) -> None:
        """Use double precision floating point numbers in data management."""
        self._is_float32 = False

    def is_float32(self) -> bool:
        """Return if single precision in data management, else double precision."""
        return self._is_float32
