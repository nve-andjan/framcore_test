"""
Event system.

All code in the core use these functions to communicate events.

Calling systems (e.g. workflow codes) can get events by hooking into SEND_EVENT_CHANNEL.
"""

_EVENT_HANDLER = None


def set_event_handler(handler: object | None) -> None:
    """Set event handler if any."""
    if handler is not None and (not hasattr(handler, "handle_event") or not callable(handler.handle_event)):
        message = "Given handler does not implement handle_event."
        raise ValueError(message)
    global _EVENT_HANDLER  # noqa: PLW0603 # TODO: unsafe?
    _EVENT_HANDLER = handler


def get_event_handler() -> object | None:
    """Get event handler if any."""
    return _EVENT_HANDLER


def send_event(sender: object, event_type: str, **kwargs: dict[str, object]) -> None:
    """All events in core should use this."""
    if _EVENT_HANDLER is None:
        print(event_type, kwargs)
    else:
        _EVENT_HANDLER.handle_event(sender, event_type, **kwargs)


def send_warning_event(sender: object, message: str) -> None:
    """Use this to send warning event."""
    send_event(sender, "warning", message=message)


def send_error_event(sender: object, message: str, exception_type_name: str, traceback: str) -> None:
    """Use this to send error event."""
    send_event(sender, "error", message=message, exception_type_name=exception_type_name, traceback=traceback)


def send_info_event(sender: object, message: str) -> None:
    """Use this to send info event."""
    send_event(sender, "info", message=message)


def send_debug_event(sender: object, message: str) -> None:
    """Use this to send debug event."""
    send_event(sender, "debug", message=message)
