"""Gymnasium environment that wraps the Battleship engine."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, TypeVar, cast

try:  # Python < 3.10 support
    from typing import TypeAlias
except ImportError:  # pragma: no cover - fallback for interpreter used in tests
    from typing_extensions import TypeAlias


import numpy as np
import numpy.typing as npt
from gymnasium import Env
from gymnasium.spaces import Box, Discrete, Space

if TYPE_CHECKING:  # pragma: no cover - typing-only shim
    _ObsT = TypeVar("_ObsT")
    _ActT = TypeVar("_ActT")

    class GymnasiumEnv(Generic[_ObsT, _ActT]):
        def reset(
            self, *, seed: int | None = None, options: dict[str, Any] | None = None
        ) -> tuple[_ObsT, dict[str, Any]]:
            ...

else:
    GymnasiumEnv = Env

from battleship.engine.board import Board, CellState
from battleship.engine.instrumented_game import InstrumentedBattleshipGame
from battleship.engine.game import GamePhase, Player
from battleship.engine.ship import Coordinate, Orientation, Ship, ShipType
from battleship.telemetry import (
    get_logger as get_otel_logger,
    get_tracer as get_otel_tracer,
    record_game_metric,
)

BOARD_SIZE = 10
NUM_CELLS = BOARD_SIZE * BOARD_SIZE
BASE_NUM_CHANNELS = 6
INVALID_ACTION_PENALTY = -0.1
HIT_REWARD = 0.1
MISS_PENALTY = -0.01
WIN_REWARD = 1.0
LOSE_PENALTY = -1.0
MAX_STEPS = 400
PLACEMENT_COMPLETION_REWARD = 0.05
PLACEMENT_SUCCESS_REWARD = 0.01

SHIP_TYPES: tuple[ShipType, ...] = tuple(ShipType)
ORIENTATIONS: tuple[Orientation, ...] = tuple(Orientation)
PLACEMENT_PER_SHIP = NUM_CELLS * len(ORIENTATIONS)

NDArrayFloat: TypeAlias = npt.NDArray[np.float32]
ActionMask: TypeAlias = npt.NDArray[np.int8]
OpponentPolicy = Callable[[NDArrayFloat, Dict[str, Any]], int]

logger = get_otel_logger("battleship.env")


@dataclass
class StepOutcome:
    agent_hit: bool = False
    agent_miss: bool = False
    invalid_action: bool = False
    placement_complete: bool = False
    winner: Player | None = None


@dataclass(frozen=True)
class PlacementAction:
    """Decoded placement command."""

    ship_type: ShipType
    coord: Coordinate
    orientation: Orientation


class BattleshipEnv(GymnasiumEnv[NDArrayFloat, int]):
    """Single-agent Battleship environment with optional agent-driven placement phase."""

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(
        self,
        render_mode: str | None = None,
        rng_seed: int | None = None,
        allow_agent_placement: bool = False,
        allow_opponent_placement: bool = False,
        opponent_policy: OpponentPolicy | None = None,
        opponent_placement_policy: OpponentPolicy | None = None,
    ) -> None:
        self.render_mode = render_mode
        self._base_seed = rng_seed
        self.rng = random.Random(rng_seed)
        self.allow_agent_placement = allow_agent_placement
        self.allow_opponent_placement = allow_opponent_placement
        self.opponent_policy = opponent_policy
        self.opponent_placement_policy = opponent_placement_policy

        placement_channels = len(SHIP_TYPES) + 1 if allow_agent_placement else 0
        self.num_channels = BASE_NUM_CHANNELS + placement_channels

        total_actions = NUM_CELLS
        if allow_agent_placement or allow_opponent_placement:
            total_actions += len(SHIP_TYPES) * PLACEMENT_PER_SHIP
        self.action_space = cast(Space[int], Discrete(total_actions))
        self.observation_space = Box(
            low=0.0,
            high=1.0,
            shape=(self.num_channels, BOARD_SIZE, BOARD_SIZE),
            dtype=np.float32,
        )

        self.game: InstrumentedBattleshipGame | None = None
        self.last_opponent_shot: Coordinate | None = None
        self.last_player_shot: Coordinate | None = None
        self.done = False
        self.step_count = 0
        self.probability_map: NDArrayFloat = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.float32)
        self.phase: str = "firing"
        self._pending_ships: set[ShipType] = set()
        self._opponent_pending_ships: set[ShipType] = set()
        self._ship_type_to_idx: dict[ShipType, int] = {
            ship: idx for idx, ship in enumerate(SHIP_TYPES)
        }
        self._episode_id = 0
        self._tracer = get_otel_tracer("battleship.env")

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[NDArrayFloat, dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self.rng.seed(seed)
        elif self._base_seed is not None and self.game is None:
            self.rng.seed(self._base_seed)

        self._episode_id += 1
        start = time.perf_counter()
        with self._tracer.start_as_current_span("battleship.env.reset") as span:
            span.set_attribute("episode_id", self._episode_id)
            span.set_attribute("allow_agent_placement", self.allow_agent_placement)
            span.set_attribute("allow_opponent_placement", self.allow_opponent_placement)

            game_seed = self.rng.randint(0, 2**31 - 1)
            self.game = InstrumentedBattleshipGame(rng_seed=game_seed)
            for player in Player:
                self.game.boards[player] = Board(owner=player.value)

            self._pending_ships = set()
            self._opponent_pending_ships = set()
            self.game.phase = GamePhase.SETUP
            self.game.current_player = Player.PLAYER1
            self.game.winner = None

            if self.allow_agent_placement:
                self.phase = "placement"
                self._pending_ships = set(SHIP_TYPES)
            else:
                self.phase = "firing"
                self._randomly_place_player(Player.PLAYER1)

            if self.allow_opponent_placement:
                self._opponent_pending_ships = set(SHIP_TYPES)
                self._execute_opponent_manual_placement()
            else:
                self._randomly_place_player(Player.PLAYER2)

            if not self.allow_agent_placement:
                self._enter_in_progress_phase()

            self.last_opponent_shot = None
            self.last_player_shot = None
            self.done = False
            self.step_count = 0
            self.probability_map = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.float32)

            observation = self._get_observation()
            info = {
                "action_mask": self._legal_action_mask(),
                "phase": self.phase,
                "state": self.get_state_for_player(Player.PLAYER1),
            }
            record_game_metric("battleship_env_reset_total", 1)
            duration_ms = (time.perf_counter() - start) * 1000
            span.set_attribute("latency_ms", duration_ms)
            record_game_metric("battleship_env_reset_latency_ms", duration_ms)
        logger.info(
            "env_reset phase=%s allow_agent_placement=%s allow_opponent_placement=%s",
            self.phase,
            self.allow_agent_placement,
            self.allow_opponent_placement,
        )
        return observation, info

    def step(self, action: int) -> tuple[NDArrayFloat, float, bool, bool, dict[str, Any]]:
        if self.game is None:
            raise RuntimeError("Environment must be reset before stepping.")
        if self.done:
            raise RuntimeError("Cannot call step() on a terminated episode.")

        if self.allow_agent_placement and self.phase == "placement":
            return self._step_placement(action)
        return self._step_firing(action)

    def _step_placement(
        self, action: int
    ) -> tuple[NDArrayFloat, float, bool, bool, dict[str, Any]]:
        if self.game is None:
            raise RuntimeError("Game not initialised.")

        outcome = StepOutcome()
        decoded = self._decode_action(action)
        terminated = truncated = False
        start = time.perf_counter()
        with self._tracer.start_as_current_span("battleship.env.step") as span:
            span.set_attribute("episode_id", self._episode_id)
            span.set_attribute("phase", "placement")
            span.set_attribute("action_index", action)

            if not isinstance(decoded, PlacementAction):
                outcome.invalid_action = True
                reward = self._calculate_reward(outcome)
                info = {
                    "invalid_action": True,
                    "action_mask": self._legal_action_mask(),
                    "phase": self.phase,
                    "state": self.get_state_for_player(Player.PLAYER1),
                }
                ship_name = decoded.ship_type.name if isinstance(decoded, PlacementAction) else None
                logger.warning(
                    "invalid_action",
                    extra={
                        "phase": self.phase,
                        "reason": "placement",
                        "ship_type": ship_name,
                        "actor": "agent",
                    },
                )
                observation = self._get_observation()
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_step_telemetry(
                    span, "placement", outcome, reward, terminated, truncated, False, duration_ms
                )
                return observation, reward, terminated, truncated, info

            span.set_attribute("placement.ship_type", decoded.ship_type.name)
            span.set_attribute("placement.row", decoded.coord.row)
            span.set_attribute("placement.col", decoded.coord.col)
            span.set_attribute("placement.orientation", decoded.orientation.value)

            if decoded.ship_type not in self._pending_ships:
                outcome.invalid_action = True
                reward = self._calculate_reward(outcome)
                info = {
                    "invalid_action": True,
                    "action_mask": self._legal_action_mask(),
                    "phase": self.phase,
                    "state": self.get_state_for_player(Player.PLAYER1),
                }
                logger.warning(
                    "invalid_action",
                    extra={
                        "phase": self.phase,
                        "reason": "placement_pending",
                        "actor": "agent",
                    },
                )
                observation = self._get_observation()
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_step_telemetry(
                    span, "placement", outcome, reward, terminated, truncated, False, duration_ms
                )
                return observation, reward, terminated, truncated, info

            player_board = self.game.boards[Player.PLAYER1]
            ship = Ship(decoded.ship_type, decoded.coord, decoded.orientation)
            try:
                player_board.place_ship(ship)
            except ValueError:
                outcome.invalid_action = True
                reward = self._calculate_reward(outcome)
                info = {
                    "invalid_action": True,
                    "action_mask": self._legal_action_mask(),
                    "phase": self.phase,
                    "state": self.get_state_for_player(Player.PLAYER1),
                }
                logger.warning(
                    "invalid_action",
                    extra={
                        "phase": self.phase,
                        "reason": "placement_conflict",
                        "actor": "agent",
                    },
                )
                observation = self._get_observation()
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_step_telemetry(
                    span, "placement", outcome, reward, terminated, truncated, False, duration_ms
                )
                return observation, reward, terminated, truncated, info

            self._pending_ships.remove(decoded.ship_type)
            reward = PLACEMENT_SUCCESS_REWARD
            if not self._pending_ships:
                self._begin_firing_phase()
                outcome.placement_complete = True
                logger.info("player_placement_complete", extra={"actor": "agent"})

            self.step_count += 1
            reward += self._calculate_reward(outcome)
            observation = self._get_observation()
            info = {
                "action_mask": self._legal_action_mask(),
                "phase": self.phase,
                "state": self.get_state_for_player(Player.PLAYER1),
            }
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_step_telemetry(
                span,
                "placement",
                outcome,
                reward,
                terminated,
                truncated,
                not outcome.invalid_action,
                duration_ms,
            )
            return observation, reward, terminated, truncated, info

    def _step_firing(self, action: int) -> tuple[NDArrayFloat, float, bool, bool, dict[str, Any]]:
        if self.game is None:
            raise RuntimeError("Environment must be reset before stepping.")

        outcome = StepOutcome()
        decoded = self._decode_action(action)
        start = time.perf_counter()
        terminated = False
        truncated = False
        with self._tracer.start_as_current_span("battleship.env.step") as span:
            span.set_attribute("episode_id", self._episode_id)
            span.set_attribute("phase", "firing")
            span.set_attribute("action_index", action)

            if isinstance(decoded, PlacementAction):
                outcome.invalid_action = True
                reward = self._calculate_reward(outcome)
                info = {
                    "invalid_action": True,
                    "action_mask": self._legal_action_mask(),
                    "phase": self.phase,
                    "state": self.get_state_for_player(Player.PLAYER1),
                }
                logger.warning(
                    "invalid_action",
                    extra={"phase": self.phase, "reason": "placement_during_firing", "actor": "agent"},
                )
                observation = self._get_observation()
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_step_telemetry(
                    span, "firing", outcome, reward, terminated, truncated, False, duration_ms
                )
                return observation, reward, terminated, truncated, info

            target_coord = decoded
            span.set_attribute("coord.row", target_coord.row)
            span.set_attribute("coord.col", target_coord.col)

            if not self._is_fire_action_legal(target_coord):
                outcome.invalid_action = True
                reward = self._calculate_reward(outcome)
                info = {
                    "invalid_action": True,
                    "action_mask": self._legal_action_mask(),
                    "phase": self.phase,
                    "state": self.get_state_for_player(Player.PLAYER1),
                }
                logger.warning(
                    "invalid_action",
                    extra={
                        "phase": self.phase,
                        "reason": "fire_illegal",
                        "row": target_coord.row,
                        "col": target_coord.col,
                        "actor": "agent",
                    },
                )
                observation = self._get_observation()
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_step_telemetry(
                    span, "firing", outcome, reward, terminated, truncated, False, duration_ms
                )
                return observation, reward, terminated, truncated, info

            # Agent move
            cell_state, hit_ship = self.game.make_move(Player.PLAYER1, target_coord)
            self.last_player_shot = target_coord
            if cell_state is CellState.HIT:
                outcome.agent_hit = True
                if hit_ship and hit_ship.is_sunk():
                    self._update_probability_map(target_coord)
            else:
                outcome.agent_miss = True

            phase: GamePhase = self.game.phase
            if phase is GamePhase.FINISHED:
                outcome.winner = self.game.winner
                terminated = True
                self.done = True
            else:
                opp_coord = self._choose_opponent_action()
                _, _ = self.game.make_move(Player.PLAYER2, opp_coord)
                self.last_opponent_shot = opp_coord
                phase = self.game.phase
                if phase is GamePhase.FINISHED:
                    outcome.winner = self.game.winner
                    terminated = True
                    self.done = True

            self.step_count += 1
            if not self.done and self.step_count >= MAX_STEPS:
                truncated = True
                self.done = True

            reward = self._calculate_reward(outcome)
            observation = self._get_observation()
            info = {
                "action_mask": self._legal_action_mask(),
                "winner": outcome.winner.name if outcome.winner else None,
                "phase": self.phase,
                "state": self.get_state_for_player(Player.PLAYER1),
            }
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_step_telemetry(
                span,
                "firing",
                outcome,
                reward,
                terminated,
                truncated,
                not outcome.invalid_action,
                duration_ms,
            )
            return observation, reward, terminated, truncated, info

    def render(self) -> None:
        if self.render_mode not in {"human", "ansi"}:
            return
        if self.game is None:
            print("Game not started.")
            return

        def render_board(board: Board, show_ships: bool) -> str:
            rows = []
            header = "   " + " ".join(f"{c+1:>2}" for c in range(BOARD_SIZE))
            rows.append(header)
            for r in range(BOARD_SIZE):
                line = [f"{r:>2} "]
                for c in range(BOARD_SIZE):
                    coord = Coordinate(r, c)
                    cell = board.get_cell_state(coord)
                    symbol = "."
                    if cell is CellState.HIT:
                        symbol = "X"
                    elif cell is CellState.MISS:
                        symbol = "o"
                    elif show_ships:
                        for ship in board.ships:
                            if coord in ship.coordinates():
                                symbol = "S"
                                break
                    line.append(f"{symbol:>2}")
                rows.append("".join(line))
            return "\n".join(rows)

        print("Player board:")
        print(render_board(self.game.boards[Player.PLAYER1], True))
        print("\nOpponent board (shots only):")
        print(render_board(self.game.boards[Player.PLAYER2], False))

    def close(self) -> None:
        self.game = None

    # Helper methods
    def _legal_action_mask(self) -> ActionMask:
        mask: ActionMask = np.zeros(self.action_space.n, dtype=np.int8)
        if self.game is None:
            return mask

        if self.allow_agent_placement and self.phase == "placement":
            return self._placement_mask_for_player(Player.PLAYER1, self._pending_ships)

        mask[:NUM_CELLS] = self._legal_shot_mask_for_player(Player.PLAYER1)
        return mask

    def _is_fire_action_legal(self, coord: Coordinate) -> bool:
        mask = self._legal_shot_mask_for_player(Player.PLAYER1)
        action = self._coord_to_action(coord)
        if not 0 <= action < NUM_CELLS:
            return False
        return bool(mask[action])

    def _choose_opponent_action(self) -> Coordinate:
        mask = self._legal_shot_mask_for_player(Player.PLAYER2)
        if not mask.any():
            return Coordinate(0, 0)

        if self.opponent_policy is None:
            action_idx = self._random_action_from_mask(mask)
        else:
            action_idx = self._call_opponent_policy(self.opponent_policy, mask, "firing")
            if not self._is_mask_action_legal(mask, action_idx):
                action_idx = self._random_action_from_mask(mask)
        return self._action_to_coord(action_idx)

    def _legal_shot_mask_for_player(self, player: Player) -> ActionMask:
        mask: ActionMask = np.zeros(NUM_CELLS, dtype=np.int8)
        if self.game is None:
            return mask
        target_board = self.game.boards[player.opponent()]
        idx = 0
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                coord = Coordinate(row, col)
                if target_board.get_cell_state(coord) is CellState.UNKNOWN:
                    mask[idx] = 1
                idx += 1
        return mask

    def _random_action_from_mask(self, mask: ActionMask) -> int:
        legal = np.flatnonzero(mask)
        if legal.size == 0:
            return 0
        return int(self.rng.choice(legal.tolist()))

    @staticmethod
    def _is_mask_action_legal(mask: ActionMask, action: int) -> bool:
        return 0 <= action < mask.shape[0] and bool(mask[action])

    def _placement_mask_for_player(self, player: Player, pending: set[ShipType]) -> ActionMask:
        mask: ActionMask = np.zeros(self.action_space.n, dtype=np.int8)
        if self.game is None:
            return mask
        board = self.game.boards[player]
        for ship_type in pending:
            ship_idx = self._ship_type_to_idx[ship_type]
            for orientation_idx, orientation in enumerate(ORIENTATIONS):
                for row in range(BOARD_SIZE):
                    for col in range(BOARD_SIZE):
                        coord = Coordinate(row, col)
                        ship = Ship(ship_type, coord, orientation)
                        if board.can_place_ship(ship):
                            action_idx = self._placement_indices(ship_idx, orientation_idx, coord)
                            mask[action_idx] = 1
        return mask

    def _call_opponent_policy(
        self,
        policy: Callable[[NDArrayFloat, dict[str, Any]], int],
        mask: ActionMask,
        phase_label: str,
    ) -> int:
        opp_obs = self._build_observation_for_player(Player.PLAYER2)
        context = {
            "action_mask": mask,
            "phase": phase_label,
            "state": self.get_state_for_player(Player.PLAYER2),
        }
        try:
            return int(policy(opp_obs, context))
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError("Opponent policy failed to produce an action.") from exc

    def _calculate_reward(self, outcome: StepOutcome) -> float:
        reward = 0.0
        if outcome.invalid_action:
            return INVALID_ACTION_PENALTY
        if outcome.agent_hit:
            reward += HIT_REWARD
        if outcome.agent_miss:
            reward += MISS_PENALTY
        if outcome.placement_complete:
            reward += PLACEMENT_COMPLETION_REWARD
        if outcome.winner is Player.PLAYER1:
            reward += WIN_REWARD
        elif outcome.winner is Player.PLAYER2:
            reward += LOSE_PENALTY
        return reward

    def _get_observation(self) -> NDArrayFloat:
        return self._build_observation_for_player(Player.PLAYER1)

    def _record_step_telemetry(
        self,
        span,
        phase: str,
        outcome: StepOutcome,
        reward: float,
        terminated: bool,
        truncated: bool,
        action_valid: bool,
        duration_ms: float,
    ) -> None:
        span.set_attribute("terminated", terminated)
        span.set_attribute("truncated", truncated)
        span.set_attribute("invalid_action", not action_valid)
        span.set_attribute("reward", reward)
        reward_type = "invalid"
        if not outcome.invalid_action:
            if outcome.agent_hit:
                reward_type = "hit"
            elif outcome.agent_miss:
                reward_type = "miss"
            elif outcome.placement_complete:
                reward_type = "placement_complete"
            elif outcome.winner or terminated:
                reward_type = "terminal"
            else:
                reward_type = "neutral"
        span.set_attribute("reward_type", reward_type)

        record_game_metric(
            "battleship_env_actions_total",
            1,
            {"phase": phase, "result": "valid" if action_valid else "invalid"},
        )
        record_game_metric(
            "battleship_env_step_latency_ms",
            duration_ms,
            {"phase": phase},
        )
        if reward >= 0:
            record_game_metric(
                "battleship_env_rewards_total",
                reward,
                {"phase": phase, "type": reward_type},
            )
        else:
            record_game_metric(
                "battleship_env_negative_rewards_total",
                abs(reward),
                {"phase": phase, "type": reward_type},
            )
        if outcome.agent_hit:
            record_game_metric("battleship_env_hits_total", 1, {"phase": phase})
        if outcome.agent_miss:
            record_game_metric("battleship_env_misses_total", 1, {"phase": phase})
        if outcome.invalid_action:
            record_game_metric("battleship_env_invalid_actions_total", 1, {"phase": phase})
        if outcome.placement_complete:
            record_game_metric("battleship_env_placement_complete_total", 1, {})

        if outcome.winner:
            result = "win" if outcome.winner is Player.PLAYER1 else "loss"
            record_game_metric("battleship_env_episode_completed_total", 1, {"result": result})
            span.set_attribute("winner", outcome.winner.name)
        elif truncated:
            record_game_metric("battleship_env_episode_completed_total", 1, {"result": "truncated"})

    def _build_observation_for_player(self, player: Player) -> NDArrayFloat:
        obs: NDArrayFloat = np.zeros((self.num_channels, BOARD_SIZE, BOARD_SIZE), dtype=np.float32)
        if self.game is None:
            return obs

        player_board = self.game.boards[player]
        opponent_board = self.game.boards[player.opponent()]

        for ship in player_board.ships:
            for coord in ship.coordinates():
                obs[0, coord.row, coord.col] = 1.0
                if player_board.get_cell_state(coord) is CellState.HIT:
                    obs[1, coord.row, coord.col] = 1.0

        for coord, state in opponent_board.shots.items():
            obs[2, coord.row, coord.col] = 1.0
            if state is CellState.HIT:
                obs[3, coord.row, coord.col] = 1.0

        last_enemy_shot = (
            self.last_opponent_shot if player is Player.PLAYER1 else self.last_player_shot
        )
        if last_enemy_shot:
            obs[4, last_enemy_shot.row, last_enemy_shot.col] = 1.0

        obs[5, :, :] = self.step_count % 2

        if self.allow_agent_placement:
            base = BASE_NUM_CHANNELS
            for idx, ship_type in enumerate(SHIP_TYPES):
                value = 1.0 if ship_type in self._pending_ships else 0.0
                obs[base + idx, :, :] = value
            phase_channel = base + len(SHIP_TYPES)
            obs[phase_channel, :, :] = 1.0 if self.phase == "placement" else 0.0
        return obs

    def _update_probability_map(self, coord: Coordinate) -> None:
        self.probability_map[coord.row, coord.col] += 0.1

    def get_state_for_player(self, player: Player) -> dict[str, Any]:
        """Return a snapshot describing the game from a specific perspective."""
        if self.game is None:
            raise RuntimeError("Game not initialised.")
        state = self.game.get_state()
        return {
            "phase": state.phase,
            "current_player": state.current_player,
            "winner": state.winner,
            "player": state.boards[player],
            "opponent": state.boards[player.opponent()],
        }

    @staticmethod
    def _coord_to_action(coord: Coordinate) -> int:
        return coord.row * BOARD_SIZE + coord.col

    @staticmethod
    def _action_to_coord(action: int) -> Coordinate:
        return Coordinate(action // BOARD_SIZE, action % BOARD_SIZE)

    def _decode_action(self, action: int) -> Coordinate | PlacementAction:
        if action < NUM_CELLS:
            return Coordinate(action // BOARD_SIZE, action % BOARD_SIZE)
        if not (self.allow_agent_placement or self.allow_opponent_placement):
            raise ValueError("Placement actions unavailable in this mode.")
        placement_idx = action - NUM_CELLS
        ship_block = placement_idx // PLACEMENT_PER_SHIP
        if ship_block >= len(SHIP_TYPES):
            raise ValueError("Placement action index out of range.")
        remainder = placement_idx % PLACEMENT_PER_SHIP
        orientation_idx = remainder // NUM_CELLS
        cell_idx = remainder % NUM_CELLS
        ship_type = SHIP_TYPES[ship_block]
        orientation = ORIENTATIONS[orientation_idx]
        coord = Coordinate(cell_idx // BOARD_SIZE, cell_idx % BOARD_SIZE)
        return PlacementAction(ship_type, coord, orientation)

    def _placement_indices(self, ship_idx: int, orientation_idx: int, coord: Coordinate) -> int:
        base = NUM_CELLS + ship_idx * PLACEMENT_PER_SHIP
        return base + orientation_idx * NUM_CELLS + self._coord_to_action(coord)

    def _begin_firing_phase(self) -> None:
        self._pending_ships.clear()
        self._enter_in_progress_phase()

    def _randomly_place_player(self, player: Player) -> None:
        if self.game is None:
            raise RuntimeError("Game not initialised.")
        self.game.boards[player].random_placement(self.rng)

    def _execute_opponent_manual_placement(self) -> None:
        if self.game is None:
            raise RuntimeError("Game not initialised.")
        pending: set[ShipType] = set(SHIP_TYPES)
        self._opponent_pending_ships = pending
        board = self.game.boards[Player.PLAYER2]
        policy = self.opponent_placement_policy or self.opponent_policy
        attempts = 0
        max_attempts = 5000
        while pending and attempts < max_attempts:
            mask = self._placement_mask_for_player(Player.PLAYER2, pending)
            if not mask.any():
                break
            if policy is None:
                action_idx = self._random_action_from_mask(mask)
            else:
                action_idx = self._call_opponent_policy(policy, mask, "opponent_placement")
                if not self._is_mask_action_legal(mask, action_idx):
                    action_idx = self._random_action_from_mask(mask)
            decoded = self._decode_action(action_idx)
            if not isinstance(decoded, PlacementAction):
                attempts += 1
                continue
            ship = Ship(decoded.ship_type, decoded.coord, decoded.orientation)
            try:
                board.place_ship(ship)
            except ValueError:
                attempts += 1
                continue
            pending.remove(decoded.ship_type)
            attempts += 1

        if pending:
            board.random_placement(self.rng)
            logger.warning(
                "opponent_manual_placement_fallback",
                extra={"remaining": len(pending), "actor": "opponent"},
            )

        self._opponent_pending_ships = set()

        logger.info("opponent_manual_placement_complete", extra={"actor": "opponent"})

    def _enter_in_progress_phase(self) -> None:
        if self.game is None:
            raise RuntimeError("Game not initialised.")
        self.game.phase = GamePhase.IN_PROGRESS
        self.game.current_player = Player.PLAYER1
        self.game.winner = None
        self.phase = "firing"
        logger.info("env_phase_transition", extra={"phase": self.phase})
