# ADR 0001 – Core Technology Stack

- **Status**: Accepted
- **Date**: 2024-01-01
- **Owners**: Battleship-RL Engineering

## Context

Battleship-RL spans a deterministic Battleship engine, RL training pipeline, FastAPI backend, and future web UI. Early stabilization depends on locking key technology choices so contributors can reason about dependencies, tooling, and deployment strategies. The stack must support Gymnasium environments, DQN agents, telemetry, and a browser-only client while integrating with enterprise observability and identity providers.

## Decision

1. **Python 3.11 + Poetry** – Authoritative language/runtime for engine, API, env, and RL agents, managed via Poetry for reproducible deps and lockfiles.
2. **FastAPI + Uvicorn** – Backend REST/WebSocket framework providing async handlers, dependency injection, and Pydantic schemas.
3. **Gymnasium + PyTorch** – Gymnasium defines the environment contract; PyTorch powers DQN agents/training loops for reproducible RL experiments.
4. **SQL Server** – Authoritative relational store for users, rooms, matches, telemetry metadata, and training jobs, aligning with enterprise infra.
5. **OpenTelemetry (Python + JS SDKs)** – Shared instrumentation layer across engine, API, trainer, and browser UI exporting via OTLP.
6. **Auth0 (OAuth/OIDC)** – External identity provider issuing JWTs verified by FastAPI middleware.
7. **Pygame UI + Future Web UI** – Pygame remains for local visualization while the roadmap targets a Canvas/DOM browser client communicating with FastAPI.

## Consequences

- Aligning on Python/Poetry simplifies packaging, lint/type-check integration, and deployment images.
- FastAPI and Gymnasium encourage async-friendly APIs and deterministic env contracts, but contributors must understand dependency injection and Gym step/reset semantics.
- SQL Server introduces ODBC/pytds dependencies; local dev may need containers or Azure SQL instances.
- OTEL across Python + JS mandates consistent attribute naming and requires stubs for local development to avoid noisy exporters.
- Auth0 integration standardizes auth flows but necessitates JWT validation middleware and secrets management per environment.
