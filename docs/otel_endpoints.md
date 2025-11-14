# OpenTelemetry Endpoints

This project currently wires a small observability stack through the
`docker-compose.training.yml` file. The following endpoints are active when the
stack is running.

## Metrics

- **Collector Prometheus exporter**: `http://otel-collector:9464/metrics`
  - Exposes metrics received via OTLP so Prometheus can scrape them.

## Traces

- **Trainer OTLP target**: `http://otel-collector:4317`
  - The trainer container sends OTLP gRPC traces/metrics to the collector via
    this endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT`).
- **Collector → Tempo**: `tempo:4317`
  - Defined in `ops/otel/config.yaml` as the OTLP gRPC exporter for traces.

## Logs

- _(Not yet configured)_ – the current collector config does not export logs.
  Once a log pipeline is added, document the endpoint here.
