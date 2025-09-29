from framcore.components import Component


def get_supported_components(
    components: dict[str, Component],
    supported_types: tuple[type[Component]],
    forbidden_types: tuple[type[Component]],
) -> dict[str, Component]:
    """Return simplified version of components in compliance with specified component types."""
    output: dict[str, Component] = {}
    errors: list[str] = []

    _simplify_until_supported(
        output,
        errors,
        components,
        supported_types,
        forbidden_types,
    )

    if errors:
        message = "\n".join(errors)
        raise ValueError(message)

    return output


def _simplify_until_supported(
    output: dict[str, Component],
    errors: list[str],
    candidates: dict[str, Component],
    supported_types: tuple[type[Component]],
    forbidden_types: tuple[type[Component]],
) -> None:
    for name, component in candidates.items():
        if isinstance(component, forbidden_types):
            message = f"{component.get_top_parent()} has forbidden component {component}"
            errors.append(message)

        elif isinstance(component, supported_types):
            output[name] = component

        else:
            simpler_components = component.get_simpler_components(name)

            if not simpler_components:
                message = (
                    f"Failed to support component. Reached bottom level component {component} with top level "
                    f"parent {component.get_top_parent()}. No component in the hierarchy was supported."
                )
                errors.append(message)

            else:
                _simplify_until_supported(
                    output,
                    errors,
                    simpler_components,
                    supported_types,
                    forbidden_types,
                )
