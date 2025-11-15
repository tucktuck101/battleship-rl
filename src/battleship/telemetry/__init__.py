"""Public telemetry helpers for Battleship RL."""

from __future__ import annotations

from .config import TelemetryConfig
from .config import init_telemetry as _base_init_telemetry
from .config import load_telemetry_config
from .logger import get_logger, init_logging
from .metrics import get_meter, init_metrics, record_game_metric
from .tracer import get_tracer, init_tracing

__all__ = [
    "TelemetryConfig",
    "get_logger",
    "get_tracer",
    "get_meter",
    "record_game_metric",
    "init_logging",
    "init_tracing",
    "init_metrics",
    "load_telemetry_config",
    "init_telemetry",
]


def init_telemetry(config: TelemetryConfig | None = None) -> TelemetryConfig:
    """Initialize tracing/metrics/logging based on the provided config."""

    return _base_init_telemetry(config)
