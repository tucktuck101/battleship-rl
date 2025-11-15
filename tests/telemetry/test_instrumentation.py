"""Telemetry instrumentation unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from battleship.ai.agent import AgentConfig, DQNAgent
from battleship.ai.environment import BattleshipEnv
from battleship.ai.instrumented_agent import InstrumentedDQNAgent
from battleship.telemetry import config as telemetry_config_module
from battleship.engine.board import CellState
from battleship.engine.game import BattleshipGame, GamePhase, Player
from battleship.engine.instrumented_game import InstrumentedBattleshipGame
from battleship.engine.ship import Coordinate
from battleship.telemetry import logger as logger_module
from battleship.telemetry import metrics as metrics_module
from battleship.telemetry import tracer as tracer_module
from battleship.telemetry.config import TelemetryConfig


class DummySpan:
    def __init__(self, names: list[str], span_name: str) -> None:
        self._names = names
        self._names.append(span_name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def set_attribute(self, *_):
        pass


class DummyTracer:
    def __init__(self) -> None:
        self.span_names: list[str] = []

    def start_as_current_span(self, name: str):
        return DummySpan(self.span_names, name)


def reset_singletons() -> None:
    tracer_module._TRACER = None
    tracer_module._TRACER_PROVIDER = None
    metrics_module._METER = None
    metrics_module._METER_PROVIDER = None
    metrics_module._INSTRUMENTS = {}
    logger_module._LOGGER = None


def test_lazy_init_tracer(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_singletons()
    assert tracer_module.get_tracer() is tracer_module.get_tracer()

    provider_instance = MagicMock()
    provider_instance.get_tracer.return_value = MagicMock()
    monkeypatch.setattr(tracer_module, "TracerProvider", MagicMock(return_value=provider_instance))
    monkeypatch.setattr(tracer_module, "OTLPSpanExporter", MagicMock(return_value=MagicMock()))
    tracer_module.init_tracing(
        TelemetryConfig(enable_tracing=True, otlp_traces_endpoint="http://example")
    )
    assert tracer_module._TRACER is provider_instance.get_tracer.return_value

    meter_provider = MagicMock()
    meter_provider.get_meter.return_value = MagicMock()
    monkeypatch.setattr(metrics_module, "MeterProvider", MagicMock(return_value=meter_provider))
    monkeypatch.setattr(metrics_module, "OTLPMetricExporter", MagicMock(return_value=MagicMock()))
    metrics_module.init_metrics(
        TelemetryConfig(enable_metrics=True, otlp_metrics_endpoint="http://example")
    )
    assert metrics_module._METER is meter_provider.get_meter.return_value


def test_logging_init_noop() -> None:
    reset_singletons()
    logger = logger_module.get_logger("test")
    assert logger_module.init_logging(TelemetryConfig()) is logger


def test_init_telemetry_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(telemetry_config_module, "init_tracing", lambda cfg: calls.append("tr"))
    monkeypatch.setattr(telemetry_config_module, "init_metrics", lambda cfg: calls.append("me"))
    monkeypatch.setattr(telemetry_config_module, "init_logging", lambda cfg: calls.append("lo"))

    telemetry_config_module.init_telemetry(TelemetryConfig())
    assert calls == []


def test_init_telemetry_respects_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(telemetry_config_module, "init_tracing", lambda cfg: calls.append("tr"))
    monkeypatch.setattr(telemetry_config_module, "init_metrics", lambda cfg: calls.append("me"))
    monkeypatch.setattr(telemetry_config_module, "init_logging", lambda cfg: calls.append("lo"))

    config = TelemetryConfig(enable_tracing=True, enable_logging=True)
    telemetry_config_module.init_telemetry(config)
    assert calls == ["tr", "lo"]


def test_load_telemetry_config_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    telemetry_config_module.load_telemetry_config.cache_clear()

    original_from_env = telemetry_config_module.TelemetryConfig.from_env
    calls = {"count": 0}

    def fake_from_env(**overrides):
        calls["count"] += 1
        return TelemetryConfig(enable_tracing=True)

    monkeypatch.setattr(
        telemetry_config_module.TelemetryConfig,
        "from_env",
        classmethod(lambda cls, **overrides: fake_from_env(**overrides)),
    )

    first = telemetry_config_module.load_telemetry_config()
    second = telemetry_config_module.load_telemetry_config()
    assert first is second
    assert calls["count"] == 1

    telemetry_config_module.TelemetryConfig.from_env = original_from_env  # type: ignore[assignment]


def test_instrumented_game_emits_spans(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = DummyTracer()
    metrics_calls: list[tuple[str, float, dict | None]] = []
    logger = MagicMock()

    monkeypatch.setattr("battleship.engine.instrumented_game.get_tracer", lambda *_: tracer)
    monkeypatch.setattr("battleship.engine.instrumented_game.get_logger", lambda *_: logger)
    monkeypatch.setattr(
        "battleship.engine.instrumented_game.record_game_metric",
        lambda name, value, attrs=None: metrics_calls.append((name, value, attrs)),
    )
    monkeypatch.setattr(BattleshipGame, "setup_random", lambda self: None)

    def fake_make_move(self, player, coord):
        self.phase = GamePhase.FINISHED
        self.winner = player
        return CellState.MISS, None

    monkeypatch.setattr(BattleshipGame, "make_move", fake_make_move)

    game = InstrumentedBattleshipGame(rng_seed=0)
    game.setup_random()
    assert "battleship.engine.game" in tracer.span_names
    assert "battleship.engine.setup_random" in tracer.span_names

    tracer.span_names.clear()
    metrics_calls.clear()
    game.make_move(Player.PLAYER1, Coordinate(0, 0))
    assert "battleship.engine.make_move" in tracer.span_names
    assert "battleship.engine.game_complete" in tracer.span_names
    metric_names = {name for name, _, _ in metrics_calls}
    assert "battleship_shots_total" in metric_names
    assert "battleship_game_completed_total" in metric_names


def test_instrumented_agent_records_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = DummyTracer()
    logger = MagicMock()
    metric_calls: list[str] = []

    monkeypatch.setattr("battleship.ai.instrumented_agent.get_tracer", lambda *_: tracer)
    monkeypatch.setattr("battleship.ai.instrumented_agent.get_logger", lambda *_: logger)
    monkeypatch.setattr(
        "battleship.ai.instrumented_agent.record_game_metric",
        lambda name, value, attrs=None: metric_calls.append(name),
    )

    config = AgentConfig(buffer_capacity=10, min_buffer_size=1, batch_size=1)
    agent = InstrumentedDQNAgent(obs_channels=6, num_actions=4, config=config)
    obs = np.zeros((6, 10, 10), dtype=np.float32)

    action = agent.select_action(obs, legal_actions=[0, 1], training=False)
    assert action in (0, 1)
    assert "battleship.agent.select_action" in tracer.span_names
    assert "battleship_agent_actions_total" in metric_calls
    assert "battleship_agent_action_latency_ms" in metric_calls

    metric_calls.clear()
    monkeypatch.setattr(DQNAgent, "train_step", lambda self: 0.25)
    agent.train_step()
    assert "battleship.agent.train_step" in tracer.span_names
    assert "battleship_agent_training_steps_total" in metric_calls
    assert "battleship_agent_training_loss" in metric_calls


def test_environment_records_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = DummyTracer()
    metrics: list[str] = []
    env_logger = MagicMock()

    monkeypatch.setattr("battleship.ai.environment.get_otel_tracer", lambda *_: tracer)
    monkeypatch.setattr("battleship.ai.environment.get_otel_logger", lambda *_: env_logger)
    monkeypatch.setattr("battleship.ai.environment.logger", env_logger)
    monkeypatch.setattr(
        "battleship.ai.environment.record_game_metric",
        lambda name, value, attrs=None: metrics.append(name),
    )

    env = BattleshipEnv(rng_seed=3)
    observation, info = env.reset()
    assert observation.shape == env.observation_space.shape
    assert "battleship.env.reset" in tracer.span_names

    tracer.span_names.clear()
    action_mask = info["action_mask"]
    first_action = int(np.flatnonzero(action_mask)[0])
    env.step(first_action)
    assert "battleship.env.step" in tracer.span_names
    assert "battleship_env_actions_total" in metrics
