"""Telemetry configuration helpers."""

from __future__ import annotations

from pydantic import BaseModel


class TelemetryConfig(BaseModel):
    enable_tracing: bool = False
    enable_metrics: bool = False
    enable_logging: bool = False
    otlp_traces_endpoint: str | None = None
    otlp_metrics_endpoint: str | None = None
    otlp_logs_endpoint: str | None = None
    service_name: str = "battleship"
    service_namespace: str = "game"


def init_telemetry(config: TelemetryConfig) -> None:
    from .logger import init_logging
    from .metrics import init_metrics
    from .tracer import init_tracing

    if config.enable_tracing:
        init_tracing(config)
    if config.enable_metrics:
        init_metrics(config)
    if config.enable_logging:
        init_logging(config)
