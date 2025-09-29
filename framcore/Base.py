import contextlib
import inspect
from typing import Any

from framcore.events import (
    send_debug_event,
    send_error_event,
    send_event,
    send_info_event,
    send_warning_event,
)
from framcore.fingerprints import Fingerprint

# TODO: Consider context dict | None in event-methods to support more info (e.g. process id)


class Base:
    """Core base class to share methods."""

    def _check_type(self, value, class_or_tuple) -> None:  # noqa: ANN001
        if not isinstance(value, class_or_tuple):
            message = f"Expected {class_or_tuple} for {self}, got {type(value).__name__}"
            raise TypeError(message)

    def _ensure_float(self, value: object) -> float:
        with contextlib.suppress(Exception):
            return float(value)
        message = f"Unable to convert {value} to float."
        raise ValueError(message)

    def _check_int(self, value: int, lower_bound: int | None, upper_bound: int | None) -> None:
        if lower_bound is not None and value < lower_bound:
            message = f"Value {value} is less than lower_bound {lower_bound}."
            raise ValueError(message)
        if upper_bound is not None and value > upper_bound:
            message = f"Value {value} is greater than upper_bound {upper_bound}."
            raise ValueError(message)

    def _check_float(self, value: float, lower_bound: float | None, upper_bound: float | None) -> None:
        if lower_bound is not None and value < lower_bound:
            message = f"Value {value} is less than lower_bound {lower_bound}."
            raise ValueError(message)
        if upper_bound is not None and value > upper_bound:
            message = f"Value {value} is greater than upper_bound {upper_bound}."
            raise ValueError(message)

    def _report_errors(self, errors: set[str]) -> None:
        if errors:
            n = len(errors)
            s = "s" if n > 1 else ""
            error_str = "\n".join(errors)
            message = f"Found {n} error{s}:\n{error_str}"
            raise RuntimeError(message)

    def send_event(self, event_type: str, **kwargs: dict[str, Any]) -> None:
        """All events in core should use this."""
        send_event(sender=self, event_type=event_type, **kwargs)

    def send_warning_event(self, message: str) -> None:
        """Use this to send warning event."""
        send_warning_event(sender=self, message=message)

    def send_error_event(self, message: str, exception_type_name: str, traceback: str) -> None:
        """Use this to send error event."""
        send_error_event(sender=self, message=message, exception_type_name=exception_type_name, traceback=traceback)

    def send_info_event(self, message: str) -> None:
        """Use this to send info event."""
        send_info_event(sender=self, message=message)

    def send_debug_event(self, message: str) -> None:
        """Use this to send debug event."""
        send_debug_event(sender=self, message=message)

    def get_fingerprint_default(
        self,
        refs: dict[str, str] | None = None,
        excludes: set[str] | None = None,
    ) -> Fingerprint:
        """
        Generate a Fingerprint for the object, optionally including references and excluding specified properties.

        Parameters
        ----------
        refs : dict[str, str] | None, optional
            Dictionary mapping property names to reference keys to include as references in the fingerprint.
        excludes : set[str] | None, optional
            Set of property names to exclude from the fingerprint.

        Returns
        -------
        Fingerprint
            The generated fingerprint for the object.

        """
        fingerprint = Fingerprint(source=self)

        if refs:
            for ref_prop, ref_key in refs.items():
                if ref_key is not None:
                    fingerprint.add_ref(ref_prop, ref_key)

        default_excludes = {"_parent"}

        for prop_name, prop_value in self.__dict__.items():
            if callable(prop_value) or (refs and prop_name in refs) or (excludes and prop_name in excludes) or prop_name in default_excludes:
                continue

            if prop_value is None:
                continue

            fingerprint.add(prop_name, prop_value)

        return fingerprint

    def _get_property_name(self, property_reference) -> str | None:  # noqa: ANN001
        for name, value in inspect.getmembers(self):
            if value is property_reference:
                return name
        return None

    def __repr__(self) -> str:
        """Display type and non-None fields."""
        type_name = type(self).__name__
        value_fields = []
        for k, v in vars(self).items():
            display_value = self._get_attr_str(k, v)
            if display_value is not None:
                value_fields.append(f"{k}={display_value}")
        value_fields = ", ".join(value_fields)
        return f"{type_name}({value_fields})"

    def _get_attr_str(self, key: str, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, int | float | str | bool):
            return value
        try:
            return value._get_attr_str()  # noqa: SLF001
        except Exception:
            pass
        return type(value).__name__
