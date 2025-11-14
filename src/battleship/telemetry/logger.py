"""Logging helpers with optional OpenTelemetry support."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import TelemetryConfig

_LOGGER: logging.Logger | None = None
_HANDLER_INSTALLED = False


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
    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)

    _install_root_handler(handler)
    return logger


def _install_root_handler(handler: logging.Handler) -> None:
    """Attach the OTLP logging handler to the root logger once."""
    global _HANDLER_INSTALLED
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format=(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s "
                "| trace_id=%(otelTraceID)s span_id=%(otelSpanID)s"
            ),
        )

    if not _HANDLER_INSTALLED:
        root_logger.addHandler(handler)
        _HANDLER_INSTALLED = True
