"""Instrumented DQN agent emitting OpenTelemetry data."""

from __future__ import annotations

import random
import time
from typing import Sequence, TypeAlias

import numpy as np
import numpy.typing as npt
import torch

from battleship.ai.agent import DQNAgent
from battleship.telemetry import get_logger, get_tracer, record_game_metric

StateArray: TypeAlias = npt.NDArray[np.float32]
StateLike: TypeAlias = StateArray | torch.Tensor
LegalArray: TypeAlias = npt.NDArray[np.float_]
LegalActions: TypeAlias = LegalArray | Sequence[int] | None


class InstrumentedDQNAgent(DQNAgent):
    """DQNAgent subclass that wraps key methods with traces/metrics/logging."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._logger = get_logger("battleship.agent")
        self._tracer = get_tracer("battleship.agent")

    def select_action(
        self,
        state: StateLike,
        legal_actions: LegalActions = None,
        training: bool = True,
    ) -> int:
        start = time.perf_counter()
        with self._tracer.start_as_current_span("battleship.agent.select_action") as span:
            state_tensor = self._prepare_state(state)
            legal = self._legal_actions(legal_actions)
            exploratory = False

            if training and self.epsilon > 0 and random.random() < self.epsilon:
                action = random.choice(legal)
                exploratory = True
            else:
                with torch.no_grad():
                    q_values = self.policy_net(state_tensor)["q_values"].squeeze(0)
                    masked_q = self._apply_action_mask(q_values, legal)
                    action = int(torch.argmax(masked_q).item())

            duration_ms = (time.perf_counter() - start) * 1000
            mode = "explore" if exploratory else "exploit"
            record_game_metric(
                "battleship_agent_actions_total",
                1,
                {"mode": mode},
            )
            record_game_metric(
                "battleship_agent_action_latency_ms",
                duration_ms,
                {"mode": mode},
            )
            span.set_attribute("epsilon", self.epsilon)
            span.set_attribute("exploratory", exploratory)
            span.set_attribute("action", action)
            record_game_metric("battleship_agent_epsilon", self.epsilon)
            self._logger.info(
                "select_action epsilon=%.3f action=%s exploratory=%s",
                self.epsilon,
                action,
                exploratory,
            )
            return action

    def train_step(self) -> float | None:
        start = time.perf_counter()
        with self._tracer.start_as_current_span("battleship.agent.train_step") as span:
            span.set_attribute("buffer_size", len(self.replay_buffer))
            span.set_attribute("batch_size", self.config.batch_size)
            loss = super().train_step()
            duration_ms = (time.perf_counter() - start) * 1000
            record_game_metric("battleship_agent_training_steps_total", 1)
            record_game_metric("battleship_agent_training_latency_ms", duration_ms)
            if loss is not None:
                record_game_metric("battleship_agent_training_loss", loss)
                span.set_attribute("loss", loss)
                self._logger.info("train_step loss=%.4f", loss)
            return loss
