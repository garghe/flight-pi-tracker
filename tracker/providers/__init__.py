from tracker.providers.base import FlightProvider
from tracker.providers.opensky import OpenSkyProvider

_REGISTRY: dict[str, type[FlightProvider]] = {
    "opensky": OpenSkyProvider,
}


def get_provider(name: str, **kwargs: object) -> FlightProvider:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {', '.join(_REGISTRY)}"
        )
    return cls(**kwargs)
