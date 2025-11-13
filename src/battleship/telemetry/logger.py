"""Logging helpers with optional OpenTelemetry support."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import TelemetryConfig

_LOGGER: logging.Logger | None = None


def get_logger(name: str = "battleship") -> logging.Logger:
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = logging.getLogger(name)
        _LOGGER.setLevel(logging.INFO)
    return _LOGGER


def init_logging(config: TelemetryConfig) -> logging.Logger:
    logger = get_logger(config.service_name)
    try:
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler, set_logger_provider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import Resource
    except ImportError:  # pragma: no cover
        return logger

    resource = Resource.create(
        {
            "service.name": config.service_name,
            "service.namespace": config.service_namespace,
        }
    )
    provider = LoggerProvider(resource=resource)

    if config.otlp_logs_endpoint:
        exporter = OTLPLogExporter(endpoint=config.otlp_logs_endpoint, insecure=True)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    set_logger_provider(provider)
    handler = LoggingHandler(logger_provider=provider)
    logger.addHandler(handler)
    return logger
