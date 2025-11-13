"""Instrumented DQN agent emitting OpenTelemetry data."""

from __future__ import annotations

import random
import time
from typing import Sequence, TypeAlias

import numpy as np
import numpy.typing as npt
import torch

from battleship.ai.agent import DQNAgent
from battleship.telemetry.logger import get_logger
from battleship.telemetry.metrics import record_game_metric
from battleship.telemetry.tracer import get_tracer

StateArray: TypeAlias = npt.NDArray[np.float32]
StateLike: TypeAlias = StateArray | torch.Tensor
LegalArray: TypeAlias = npt.NDArray[np.float_]
LegalActions: TypeAlias = LegalArray | Sequence[int] | None


class InstrumentedDQNAgent(DQNAgent):
    """DQNAgent subclass that wraps key methods with traces/metrics/logging."""

    def select_action(
        self,
        state: StateLike,
        legal_actions: LegalActions = None,
        training: bool = True,
    ) -> int:
        tracer = get_tracer("battleship.agent")
        logger = get_logger("battleship.agent")
        start = time.perf_counter()
        with tracer.start_as_current_span("agent.select_action") as span:
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
            record_game_metric("agent.action_latency_ms", duration_ms)
            span.set_attribute("epsilon", self.epsilon)
            span.set_attribute("exploratory", exploratory)
            span.set_attribute("action", action)
            logger.info(
                "select_action epsilon=%.3f action=%s exploratory=%s",
                self.epsilon,
                action,
                exploratory,
            )
            return action

    def train_step(self) -> float | None:
        tracer = get_tracer("battleship.agent")
        logger = get_logger("battleship.agent")
        start = time.perf_counter()
        with tracer.start_as_current_span("agent.train_step"):
            loss = super().train_step()
            duration_ms = (time.perf_counter() - start) * 1000
            record_game_metric("agent.training_steps", 1)
            record_game_metric("agent.training_latency_ms", duration_ms)
            if loss is not None:
                record_game_metric("agent.training_loss", loss)
                logger.info("train_step loss=%.4f", loss)
            return loss
