"""Telemetry configuration helpers."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict

from pydantic import BaseModel, Field


class TelemetryConfig(BaseModel):
    """Runtime configuration for telemetry exporters."""

    enable_tracing: bool = False
    enable_metrics: bool = False
    enable_logging: bool = False
    otlp_traces_endpoint: str | None = None
    otlp_metrics_endpoint: str | None = None
    otlp_logs_endpoint: str | None = None
    service_name: str = "battleship"
    service_namespace: str = "game"
    resource_attributes: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_env(cls, **overrides: Any) -> "TelemetryConfig":
        """Construct config from env vars (`BATTLESHIP_*` + `OTEL_*`)."""

        data: Dict[str, Any] = cls().model_dump()
        data.update(overrides)

        def _bool_from_env(*names: str) -> bool | None:
            for name in names:
                value = os.getenv(name)
                if value is not None:
                    return value.strip().lower() in {"1", "true", "yes", "on"}
            return None

        bool_fields = {
            "enable_tracing": ("BATTLESHIP_ENABLE_TRACING", "OTEL_TRACES_ENABLED"),
            "enable_metrics": ("BATTLESHIP_ENABLE_METRICS", "OTEL_METRICS_ENABLED"),
            "enable_logging": ("BATTLESHIP_ENABLE_LOGGING", "OTEL_LOGS_ENABLED"),
        }
        for field, env_names in bool_fields.items():
            env_value = _bool_from_env(*env_names)
            if env_value is not None:
                data[field] = env_value

        base_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        metrics_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
        logs_endpoint = os.getenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT")

        def _with_suffix(base: str | None, suffix: str) -> str | None:
            if not base:
                return None
            base = base.rstrip("/")
            return f"{base}/{suffix}"

        data.setdefault("otlp_traces_endpoint", traces_endpoint or _with_suffix(base_endpoint, "v1/traces"))
        data.setdefault("otlp_metrics_endpoint", metrics_endpoint or _with_suffix(base_endpoint, "v1/metrics"))
        data.setdefault("otlp_logs_endpoint", logs_endpoint or _with_suffix(base_endpoint, "v1/logs"))

        service_name = os.getenv("OTEL_SERVICE_NAME")
        service_namespace = os.getenv("OTEL_SERVICE_NAMESPACE")
        if service_name:
            data["service_name"] = service_name
        if service_namespace:
            data["service_namespace"] = service_namespace

        resource_env = os.getenv("OTEL_RESOURCE_ATTRIBUTES")
        if resource_env:
            attrs = {**data.get("resource_attributes", {})}
            for part in resource_env.split(","):
                if "=" not in part:
                    continue
                key, value = part.split("=", 1)
                attrs[key.strip()] = value.strip()
            data["resource_attributes"] = attrs

        # Auto-enable exporters when endpoints are configured.
        if data.get("otlp_traces_endpoint"):
            data["enable_tracing"] = data.get("enable_tracing") or True
        if data.get("otlp_metrics_endpoint"):
            data["enable_metrics"] = data.get("enable_metrics") or True
        if data.get("otlp_logs_endpoint"):
            data["enable_logging"] = data.get("enable_logging") or True

        return cls(**data)


@lru_cache(maxsize=1)
def load_telemetry_config() -> TelemetryConfig:
    """Load and cache telemetry config from the environment."""

    return TelemetryConfig.from_env()


def init_telemetry(config: TelemetryConfig | None = None) -> TelemetryConfig:
    """Initialise telemetry subsystems lazily."""

    from .logger import init_logging
    from .metrics import init_metrics
    from .tracer import init_tracing

    resolved = config or load_telemetry_config()

    if resolved.enable_tracing:
        init_tracing(resolved)
    if resolved.enable_metrics:
        init_metrics(resolved)
    if resolved.enable_logging:
        init_logging(resolved)
    return resolved
