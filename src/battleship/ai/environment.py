"""Gymnasium environment that wraps the Battleship engine."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeAlias, TypeVar, cast

import numpy as np
import numpy.typing as npt
from gymnasium import Env
from gymnasium.spaces import Box, Discrete, Space

if TYPE_CHECKING:  # pragma: no cover - typing-only shim
    _ObsT = TypeVar("_ObsT")
    _ActT = TypeVar("_ActT")

    class GymnasiumEnv(Generic[_ObsT, _ActT]):
        ...

else:
    GymnasiumEnv = Env

from battleship.engine.board import Board, CellState
from battleship.engine.game import BattleshipGame, GamePhase, Player
from battleship.engine.ship import Coordinate

BOARD_SIZE = 10
NUM_CELLS = BOARD_SIZE * BOARD_SIZE
NUM_CHANNELS = 6
INVALID_ACTION_PENALTY = -0.1
HIT_REWARD = 0.1
MISS_PENALTY = -0.01
WIN_REWARD = 1.0
LOSE_PENALTY = -1.0
MAX_STEPS = 400

NDArrayFloat: TypeAlias = npt.NDArray[np.float32]
ActionMask: TypeAlias = npt.NDArray[np.int8]


@dataclass
class StepOutcome:
    agent_hit: bool = False
    agent_miss: bool = False
    invalid_action: bool = False
    winner: Player | None = None


class BattleshipEnv(GymnasiumEnv[NDArrayFloat, int]):
    """Single-agent environment for Battleship."""

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(self, render_mode: str | None = None, rng_seed: int | None = None) -> None:
        self.render_mode = render_mode
        self._base_seed = rng_seed
        self.rng = random.Random(rng_seed)
        self.action_space = cast(Space[int], Discrete(NUM_CELLS))
        self.observation_space = Box(
            low=0.0, high=1.0, shape=(NUM_CHANNELS, BOARD_SIZE, BOARD_SIZE), dtype=np.float32
        )

        self.game: BattleshipGame | None = None
        self.last_opponent_shot: Coordinate | None = None
        self.done = False
        self.step_count = 0
        self.probability_map: NDArrayFloat = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.float32)

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[NDArrayFloat, dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self.rng.seed(seed)
        elif self._base_seed is not None and self.game is None:
            self.rng.seed(self._base_seed)

        game_seed = self.rng.randint(0, 2**31 - 1)
        self.game = BattleshipGame(rng_seed=game_seed)
        self.game.setup_random()

        self.last_opponent_shot = None
        self.done = False
        self.step_count = 0
        self.probability_map = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.float32)

        observation = self._get_observation()
        info = {"action_mask": self._legal_action_mask()}
        return observation, info

    def step(self, action: int) -> tuple[NDArrayFloat, float, bool, bool, dict[str, Any]]:
        if self.game is None:
            raise RuntimeError("Environment must be reset before stepping.")
        if self.done:
            raise RuntimeError("Cannot call step() on a terminated episode.")

        outcome = StepOutcome()
        target_coord = self._action_to_coord(action)

        if not self._is_action_legal(target_coord):
            outcome.invalid_action = True
            reward = self._calculate_reward(outcome)
            info = {"invalid_action": True, "action_mask": self._legal_action_mask()}
            return self._get_observation(), reward, False, False, info

        # Agent move
        cell_state, hit_ship = self.game.make_move(Player.PLAYER1, target_coord)
        if cell_state is CellState.HIT:
            outcome.agent_hit = True
            if hit_ship and hit_ship.is_sunk():
                self._update_probability_map(target_coord)
        else:
            outcome.agent_miss = True

        terminated = False
        truncated = False

        phase: GamePhase = self.game.phase
        if phase is GamePhase.FINISHED:
            outcome.winner = self.game.winner
            terminated = True
            self.done = True
        else:
            opponent_action = self._select_opponent_action()
            opp_coord = self._action_to_coord(opponent_action)
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
        }

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
        mask: ActionMask = np.zeros(NUM_CELLS, dtype=np.int8)
        if self.game is None:
            return mask
        board = self.game.boards[Player.PLAYER2]
        idx = 0
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                coord = Coordinate(row, col)
                if board.get_cell_state(coord) is CellState.UNKNOWN:
                    mask[idx] = 1
                idx += 1
        return mask

    def _is_action_legal(self, coord: Coordinate) -> bool:
        if self.game is None:
            return False
        board = self.game.boards[Player.PLAYER2]
        return board.get_cell_state(coord) is CellState.UNKNOWN

    def _select_opponent_action(self) -> int:
        if self.game is None:
            raise RuntimeError("Game not initialised.")
        board = self.game.boards[Player.PLAYER1]
        legal_actions = [
            self._coord_to_action(Coordinate(row, col))
            for row in range(BOARD_SIZE)
            for col in range(BOARD_SIZE)
            if board.get_cell_state(Coordinate(row, col)) is CellState.UNKNOWN
        ]
        if not legal_actions:
            return 0
        return self.rng.choice(legal_actions)

    def _calculate_reward(self, outcome: StepOutcome) -> float:
        reward = 0.0
        if outcome.invalid_action:
            return INVALID_ACTION_PENALTY
        if outcome.agent_hit:
            reward += HIT_REWARD
        if outcome.agent_miss:
            reward += MISS_PENALTY
        if outcome.winner is Player.PLAYER1:
            reward += WIN_REWARD
        elif outcome.winner is Player.PLAYER2:
            reward += LOSE_PENALTY
        return reward

    def _get_observation(self) -> NDArrayFloat:
        obs: NDArrayFloat = np.zeros((NUM_CHANNELS, BOARD_SIZE, BOARD_SIZE), dtype=np.float32)
        if self.game is None:
            return obs

        player_board = self.game.boards[Player.PLAYER1]
        opponent_board = self.game.boards[Player.PLAYER2]

        for ship in player_board.ships:
            for coord in ship.coordinates():
                obs[0, coord.row, coord.col] = 1.0
                if player_board.get_cell_state(coord) is CellState.HIT:
                    obs[1, coord.row, coord.col] = 1.0

        for coord, state in opponent_board.shots.items():
            obs[2, coord.row, coord.col] = 1.0
            if state is CellState.HIT:
                obs[3, coord.row, coord.col] = 1.0

        if self.last_opponent_shot:
            obs[4, self.last_opponent_shot.row, self.last_opponent_shot.col] = 1.0

        obs[5, :, :] = self.step_count % 2
        return obs

    def _update_probability_map(self, coord: Coordinate) -> None:
        self.probability_map[coord.row, coord.col] += 0.1

    @staticmethod
    def _action_to_coord(action: int) -> Coordinate:
        row = action // BOARD_SIZE
        col = action % BOARD_SIZE
        return Coordinate(row, col)

    @staticmethod
    def _coord_to_action(coord: Coordinate) -> int:
        return coord.row * BOARD_SIZE + coord.col
