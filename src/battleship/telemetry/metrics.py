"""Metrics helper utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from opentelemetry import metrics as otel_metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Counter, Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

if TYPE_CHECKING:  # pragma: no cover
    from .config import TelemetryConfig

_METER_PROVIDER: MeterProvider | None = None
_METER: Meter | None = None
_INSTRUMENTS: dict[str, Counter] = {}


def get_meter(name: str = "battleship") -> Meter:
    global _METER
    if _METER is None:
        _METER = otel_metrics.get_meter(name)
    return _METER


def init_metrics(config: TelemetryConfig) -> Meter:
    global _METER_PROVIDER, _METER, _INSTRUMENTS

    resource = Resource.create(
        {
            "service.name": config.service_name,
            "service.namespace": config.service_namespace,
        }
    )

    readers = []
    if config.otlp_metrics_endpoint:
        exporter = OTLPMetricExporter(endpoint=config.otlp_metrics_endpoint, insecure=True)
        readers.append(PeriodicExportingMetricReader(exporter, export_interval_millis=5000))

    provider = MeterProvider(resource=resource, metric_readers=readers)
    otel_metrics.set_meter_provider(provider)

    _METER_PROVIDER = provider
    _METER = provider.get_meter(config.service_name)
    _INSTRUMENTS = {}
    return _METER


MetricAttributes = Mapping[str, str | bool | int | float]


def record_game_metric(name: str, value: float, attrs: MetricAttributes | None = None) -> None:
    meter = get_meter()
    instrument = _INSTRUMENTS.get(name)
    if instrument is None:
        instrument = meter.create_counter(name)
        _INSTRUMENTS[name] = instrument
    instrument.add(value, attributes=attrs or {})
