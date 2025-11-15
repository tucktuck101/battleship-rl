"""Tracing helpers built on OpenTelemetry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace import Tracer

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .config import TelemetryConfig


_TRACER: Tracer | None = None
_TRACER_PROVIDER: TracerProvider | None = None


def get_tracer(name: str = "battleship") -> Tracer:
    """Return the global tracer (lazily initialised)."""
    global _TRACER
    if _TRACER is None:
        _TRACER = trace.get_tracer(name)
    return _TRACER


def init_tracing(config: TelemetryConfig) -> Tracer:
    """Initialise the TracerProvider according to the config."""
    global _TRACER, _TRACER_PROVIDER

    attributes = {
        "service.name": config.service_name,
        "service.namespace": config.service_namespace,
    }
    attributes.update(config.resource_attributes)
    resource = Resource.create(attributes)
    provider = TracerProvider(resource=resource)

    if config.otlp_traces_endpoint:
        exporter = OTLPSpanExporter(endpoint=config.otlp_traces_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _TRACER_PROVIDER = provider
    _TRACER = provider.get_tracer(config.service_name)
    return _TRACER
