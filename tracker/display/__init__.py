from tracker.display.base import Display
from tracker.display.console import ConsoleDisplay
from tracker.display.hub75 import Hub75Display

_REGISTRY: dict[str, type[Display]] = {
    "hub75": Hub75Display,
    "console": ConsoleDisplay,
}


def get_display(name: str, **kwargs: object) -> Display:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown display type '{name}'. Available: {', '.join(_REGISTRY)}"
        )
    return cls(**kwargs)
