"""Public telemetry helpers for Battleship RL."""

from __future__ import annotations

from .config import TelemetryConfig
from .config import init_telemetry as _base_init_telemetry
from .config import load_telemetry_config
from .metrics import get_meter
from .tracer import get_tracer

__all__ = [
    "TelemetryConfig",
    "get_tracer",
    "get_meter",
    "load_telemetry_config",
    "init_telemetry",
]


def init_telemetry(config: TelemetryConfig | None = None) -> TelemetryConfig:
    """Initialize tracing/metrics/logging based on the provided config."""

    return _base_init_telemetry(config)
