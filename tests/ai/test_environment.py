"""Tests for the Battleship Gymnasium environment."""

from __future__ import annotations

import numpy as np
from battleship.ai.environment import (
    BASE_NUM_CHANNELS,
    BOARD_SIZE,
    NUM_CELLS,
    BattleshipEnv,
)
from battleship.engine.game import GamePhase, Player
from battleship.engine.ship import Coordinate, Orientation, ShipType


def _first_legal_action(mask: np.ndarray) -> int:
    legal = np.flatnonzero(mask)
    assert legal.size > 0, "Expected at least one legal action"
    return int(legal[0])


def test_env_initialization_default_mode() -> None:
    env = BattleshipEnv()
    assert env.action_space.n == NUM_CELLS
    assert env.observation_space.shape == (BASE_NUM_CHANNELS, BOARD_SIZE, BOARD_SIZE)
    assert env.game is None
    env.close()


def test_env_reset_default_mode() -> None:
    env = BattleshipEnv(rng_seed=123)
    observation, info = env.reset()
    assert observation.shape == env.observation_space.shape
    mask = info["action_mask"]
    assert isinstance(mask, np.ndarray)
    assert mask.shape == (NUM_CELLS,)
    assert mask.sum() > 0
    assert info["phase"] == "firing"
    assert env.game is not None
    env.close()


def test_env_step_advances_game_default_mode() -> None:
    env = BattleshipEnv(rng_seed=7)
    _, info = env.reset()
    action = _first_legal_action(info["action_mask"])
    observation, reward, terminated, truncated, info = env.step(action)
    assert observation.shape == env.observation_space.shape
    assert np.isfinite(reward)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert info["phase"] == "firing"
    env.close()


def test_invalid_action_penalty_default_mode() -> None:
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


def test_agent_placement_extends_spaces() -> None:
    env = BattleshipEnv(rng_seed=3, allow_agent_placement=True)
    obs, info = env.reset()
    assert obs.shape == env.observation_space.shape
    expected_actions = NUM_CELLS + len(ShipType) * NUM_CELLS * len(Orientation)
    assert env.action_space.n == expected_actions
    assert info["phase"] == "placement"
    assert info["action_mask"].shape == (expected_actions,)
    assert info["action_mask"][:NUM_CELLS].sum() == 0
    env.close()


def test_agent_places_ships_and_transitions_to_firing() -> None:
    env = BattleshipEnv(rng_seed=11, allow_agent_placement=True)
    _, info = env.reset()
    assert env.game is not None
    player_board = env.game.boards[Player.PLAYER1]

    while info["phase"] == "placement":
        action = _first_legal_action(info["action_mask"])
        _, reward, terminated, truncated, info = env.step(action)
        assert reward >= 0.0 or np.isclose(reward, 0.0)
        assert not terminated
        assert not truncated

    assert len(player_board.ships) == len(ShipType)
    assert env.phase == "firing"
    assert env.game.phase is GamePhase.IN_PROGRESS
    env.close()


def test_invalid_agent_placement_penalized() -> None:
    env = BattleshipEnv(rng_seed=17, allow_agent_placement=True)
    _, info = env.reset()
    first_action = _first_legal_action(info["action_mask"])
    env.step(first_action)
    _, penalty, terminated, truncated, info = env.step(first_action)
    assert penalty < 0.0
    assert not terminated
    assert not truncated
    assert info.get("invalid_action") is True
    assert info["phase"] == "placement"
    env.close()


def test_firing_actions_work_after_agent_placement() -> None:
    env = BattleshipEnv(rng_seed=23, allow_agent_placement=True)
    _, info = env.reset()
    while info["phase"] == "placement":
        action = _first_legal_action(info["action_mask"])
        _, _, _, _, info = env.step(action)
    assert info["phase"] == "firing"
    action = _first_legal_action(info["action_mask"])
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs.shape == env.observation_space.shape
    assert np.isfinite(reward)
    assert "winner" in info
    env.close()


def test_env_custom_opponent_policy_used() -> None:
    calls: list[int] = []

    def opponent_policy(obs: np.ndarray, info: dict[str, object]) -> int:
        mask = np.asarray(info["action_mask"], dtype=np.int8)
        choice = int(np.flatnonzero(mask)[0])
        calls.append(choice)
        return choice

    env = BattleshipEnv(rng_seed=2, opponent_policy=opponent_policy)
    _, info = env.reset()
    action = _first_legal_action(info["action_mask"])
    env.step(action)
    assert calls, "Opponent policy should have been invoked"
    assert env.last_opponent_shot == Coordinate(0, 0)
    env.close()


def test_opponent_manual_placement_policy_invoked() -> None:
    phases: list[str] = []

    def placement_policy(obs: np.ndarray, info: dict[str, object]) -> int:
        mask = np.asarray(info["action_mask"], dtype=np.int8)
        choice = int(np.flatnonzero(mask)[0])
        phases.append(str(info["phase"]))
        return choice

    env = BattleshipEnv(
        rng_seed=9,
        allow_opponent_placement=True,
        opponent_placement_policy=placement_policy,
    )
    env.reset()
    assert any(phase == "opponent_placement" for phase in phases)
    opponent_board = env.game.boards[Player.PLAYER2]
    assert len(opponent_board.ships) == len(ShipType)
    env.close()
