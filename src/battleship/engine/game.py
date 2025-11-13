"""Two-player Battleship game controller."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .board import Board, CellState
from .ship import Coordinate, Ship


class GamePhase(Enum):
    """High-level lifecycle of a Battleship match."""

    SETUP = "setup"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Player(Enum):
    """Available players."""

    PLAYER1 = "player1"
    PLAYER2 = "player2"

    def opponent(self) -> Player:
        """Return the opposing player."""
        return Player.PLAYER2 if self is Player.PLAYER1 else Player.PLAYER1


@dataclass(frozen=True)
class BoardSnapshot:
    """Serializable view of a board for state queries."""

    ships: tuple[tuple[Coordinate, ...], ...]
    shots: dict[Coordinate, CellState]


@dataclass(frozen=True)
class GameState:
    """Immutable snapshot of the current game."""

    phase: GamePhase
    current_player: Player
    winner: Player | None
    boards: dict[Player, BoardSnapshot]


class BattleshipGame:
    """Coordinates gameplay between two player boards."""

    def __init__(self, rng_seed: int | None = None) -> None:
        self.boards: dict[Player, Board] = {
            Player.PLAYER1: Board(),
            Player.PLAYER2: Board(),
        }
        self.phase: GamePhase = GamePhase.SETUP
        self.current_player: Player = Player.PLAYER1
        self.winner: Player | None = None
        self._rng = random.Random(rng_seed)

    def setup_random(self) -> None:
        """Randomly place fleets for both players and start the game."""
        for board in self.boards.values():
            board.random_placement(self._rng)
        self.phase = GamePhase.IN_PROGRESS
        self.current_player = Player.PLAYER1
        self.winner = None

    def make_move(self, player: Player, coord: Coordinate) -> tuple[CellState, Ship | None]:
        """Apply a single shot, enforcing turn order and win conditions."""
        if self.phase is not GamePhase.IN_PROGRESS:
            raise RuntimeError("Game is not in progress.")
        if player is not self.current_player:
            raise RuntimeError("It is not this player's turn.")

        target_board = self.boards[player.opponent()]
        result = target_board.receive_shot(coord)

        if target_board.all_ships_sunk():
            self.winner = player
            self.phase = GamePhase.FINISHED
        else:
            self.current_player = player.opponent()

        return result

    def get_state(self) -> GameState:
        """Return an immutable view of the current match."""
        board_views = {
            player: BoardSnapshot(
                ships=tuple(tuple(ship.coordinates()) for ship in board.ships),
                shots=dict(board.shots),
            )
            for player, board in self.boards.items()
        }
        return GameState(
            phase=self.phase,
            current_player=self.current_player,
            winner=self.winner,
            boards=board_views,
        )

    def valid_moves(self, player: Player) -> list[Coordinate]:
        """Return all coordinates the player can legally target."""
        if self.phase is not GamePhase.IN_PROGRESS:
            return []
        target_board = self.boards[player.opponent()]
        moves: list[Coordinate] = []
        for row in range(target_board.size):
            for col in range(target_board.size):
                coord = Coordinate(row, col)
                if target_board.get_cell_state(coord) is CellState.UNKNOWN:
                    moves.append(coord)
        return moves
