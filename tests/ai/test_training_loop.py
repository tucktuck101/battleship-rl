"""Tests for the high-level training loop utilities."""

from __future__ import annotations

import numpy as np
import pytest

try:  # pragma: no cover - optional dependency
    import torch  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.skip("requires torch", allow_module_level=True)

from battleship.ai.training import Trainer, TrainingConfig


class DeterministicOpponent:
    """Simple opponent that always fires at the first legal cell."""

    def __init__(self) -> None:
        self.epsilon = 0.5

    def select_action(
        self, obs: np.ndarray, legal_actions, training: bool = False
    ) -> int:  # noqa: D401
        mask = np.asarray(legal_actions)
        legal = np.flatnonzero(mask)
        return int(legal[0])


def _small_config(tmp_path_factory: pytest.TempPathFactory) -> TrainingConfig:
    return TrainingConfig(
        num_episodes=1,
        max_steps_per_episode=2,
        eval_interval=50,
        eval_episodes=1,
        buffer_capacity=200,
        batch_size=8,
        min_buffer_size=1,
        save_dir=str(tmp_path_factory.mktemp("train_artifacts")),
        opponent="random",
    )


def test_trainer_supports_external_opponent(tmp_path_factory: pytest.TempPathFactory) -> None:
    config = _small_config(tmp_path_factory)
    opponent = DeterministicOpponent()
    trainer = Trainer(config, opponent_agent=opponent)
    metrics = trainer._train_episode(0)
    assert "reward" in metrics
    trainer.env.close()


def test_trainer_self_play_enables_policy_wrapper(tmp_path_factory: pytest.TempPathFactory) -> None:
    config = _small_config(tmp_path_factory)
    config.opponent = "self"
    trainer = Trainer(config)
    assert trainer.env.opponent_policy is not None
    trainer._train_episode(0)
    trainer.env.close()


def test_evaluation_restores_opponent_epsilon(tmp_path_factory: pytest.TempPathFactory) -> None:
    config = _small_config(tmp_path_factory)
    opponent = DeterministicOpponent()
    trainer = Trainer(config, opponent_agent=opponent)
    before = opponent.epsilon
    trainer._evaluate()
    assert opponent.epsilon == before
    trainer.env.close()


def test_trainer_handles_opponent_manual_placement(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    config = _small_config(tmp_path_factory)
    config.opponent_manual_placement = True
    opponent = DeterministicOpponent()
    trainer = Trainer(config, opponent_agent=opponent)
    trainer._train_episode(0)
    trainer.env.close()
