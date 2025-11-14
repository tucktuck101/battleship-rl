"""Public telemetry helpers for Battleship RL."""

from __future__ import annotations

from .config import TelemetryConfig
from .config import init_telemetry as _base_init_telemetry
from .metrics import get_meter
from .tracer import get_tracer

__all__ = [
    "TelemetryConfig",
    "get_tracer",
    "get_meter",
    "init_telemetry",
]


def init_telemetry(config: TelemetryConfig) -> None:
    """Initialize tracing/metrics/logging based on the provided config."""

    _base_init_telemetry(config)
