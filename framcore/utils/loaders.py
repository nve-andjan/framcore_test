from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from framcore.events import send_warning_event

if TYPE_CHECKING:
    from framcore import Model
    from framcore.loaders import Loader


def add_loaders_if(loaders: set, value: object | None) -> None:
    """Call value.add_loaders(loaders) if value is not None."""
    _check_type(loaders, "loaders", set)
    if value is None:
        return
    value.add_loaders(loaders)


def add_loaders(loaders: set[Loader], model: Model) -> None:
    """Add all loaders stored in Model to loaders set."""
    from framcore import Model  # noqa: PLC0415
    from framcore.components import Component, Flow, Node  # noqa: PLC0415
    from framcore.curves import Curve  # noqa: PLC0415
    from framcore.expressions import Expr  # noqa: PLC0415
    from framcore.timevectors import TimeVector  # noqa: PLC0415
    from framcore.utils import get_supported_components  # noqa: PLC0415

    _check_type(loaders, "loaders", set)
    _check_type(model, "model", Model)

    data = model.get_data()
    components = dict()

    for key, value in data.items():
        if isinstance(value, Expr):
            value.add_loaders(loaders)

        elif isinstance(value, TimeVector | Curve):
            loader = value.get_loader()
            if loader is not None:
                loaders.add(loader)

        elif isinstance(value, Component):
            components[key] = value

    graph: dict[str, Flow | Node] = get_supported_components(components, (Flow, Node), tuple())

    for c in graph.values():
        c.add_loaders(loaders)


def replace_loader_path(loaders: set[Loader], old: Path, new: Path) -> None:
    """Replace old path with new for all loaders using old path."""
    from framcore.loaders import FileLoader  # noqa: PLC0415

    _check_type(loaders, "loaders", set)

    new = _check_path(new, "new", make_absolute=True)
    old = _check_path(old, "old", error_if_not_absolute=True)

    for loader in loaders:
        try:
            source = loader.get_source()
        except Exception:
            send_warning_event(f"loader.get_source() failed for {loader}. Skipping this one.")
            continue

        if isinstance(source, Path) and old in source.parents:
            loader.set_source(new_source=new / source.relative_to(old))

        if isinstance(loader, FileLoader) and not isinstance(source, Path):
            send_warning_event(f"FileLoader.get_source() does not return Path as it should for loader {loader}. Instead of Path, got {source}")


def _check_type(value, name, expected) -> None:  # noqa: ANN001
    if not isinstance(value, expected):
        message = f"Expected {name} to be {type(expected).__name__}. Got Got {type(value).__name__}"
        raise TypeError(message)


def _check_path(
    path: Path,
    new_old: str,
    make_absolute: bool = False,
    error_if_not_absolute: bool = False,
) -> Path:
    if not isinstance(path, Path):
        message = f"{new_old} must be Path. Got {path}"
        raise ValueError(message)
    if make_absolute and not path.is_absolute():
        path = path.resolve()
    if error_if_not_absolute and not path.is_absolute():
        message = f"{new_old} must be an absolute Path. Got {path}"
        raise ValueError(message)
    return path
