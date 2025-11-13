"""Tests for the Battleship Gymnasium environment."""

from __future__ import annotations

import numpy as np
from battleship.ai.environment import BattleshipEnv


def _first_legal_action(mask: np.ndarray) -> int:
    legal = np.flatnonzero(mask)
    assert legal.size > 0, "Expected at least one legal action"
    return int(legal[0])


def test_env_initialization() -> None:
    env = BattleshipEnv()
    assert env.action_space.n == 100
    assert env.observation_space.shape == (6, 10, 10)
    assert env.game is None
    env.close()


def test_env_reset() -> None:
    env = BattleshipEnv(rng_seed=123)
    observation, info = env.reset()
    assert observation.shape == env.observation_space.shape
    mask = info["action_mask"]
    assert isinstance(mask, np.ndarray)
    assert mask.shape == (100,)
    assert mask.sum() > 0
    assert env.game is not None
    env.close()


def test_env_step_advances_game() -> None:
    env = BattleshipEnv(rng_seed=7)
    _, info = env.reset()
    action = _first_legal_action(info["action_mask"])
    observation, reward, terminated, truncated, info = env.step(action)
    assert observation.shape == env.observation_space.shape
    assert np.isfinite(reward)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "action_mask" in info
    env.close()


def test_invalid_action_penalty() -> None:
    env = BattleshipEnv(rng_seed=21)
    _, info = env.reset()
    action = _first_legal_action(info["action_mask"])
    env.step(action)
    _, penalty, terminated, truncated, info = env.step(action)
    assert penalty < 0.0
    assert not terminated
    assert not truncated
    assert info.get("invalid_action") is True
    env.close()


def test_deterministic_seeding() -> None:
    steps = 5
    env_a = BattleshipEnv(rng_seed=99)
    env_b = BattleshipEnv(rng_seed=99)

    obs_a, info_a = env_a.reset()
    obs_b, info_b = env_b.reset()
    assert np.allclose(obs_a, obs_b)
    assert np.array_equal(info_a["action_mask"], info_b["action_mask"])

    for _ in range(steps):
        action = _first_legal_action(info_a["action_mask"])
        obs_a, reward_a, term_a, trunc_a, info_a = env_a.step(action)
        obs_b, reward_b, term_b, trunc_b, info_b = env_b.step(action)
        assert np.isclose(reward_a, reward_b)
        assert np.allclose(obs_a, obs_b)
        assert term_a == term_b
        assert trunc_a == trunc_b
        if term_a or trunc_a:
            break

    env_a.close()
    env_b.close()


def test_episode_completion() -> None:
    env = BattleshipEnv(rng_seed=5)
    _, info = env.reset()
    final_info = info
    terminated = truncated = False
    for _ in range(1000):
        action = _first_legal_action(info["action_mask"])
        _, _, terminated, truncated, info = env.step(action)
        final_info = info
        if terminated or truncated:
            break
    assert terminated or truncated
    if terminated:
        assert final_info["winner"] in {"PLAYER1", "PLAYER2"}
    env.close()
