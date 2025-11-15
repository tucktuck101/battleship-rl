"""Instrumented Battleship game with telemetry hooks."""

from __future__ import annotations

import time
from typing import Any

from battleship.engine.board import CellState
from battleship.engine.game import BattleshipGame, GamePhase, Player
from battleship.engine.ship import Coordinate, Ship
from battleship.telemetry import get_logger, get_tracer, record_game_metric


class InstrumentedBattleshipGame(BattleshipGame):
    """Wraps BattleshipGame with tracing, metrics, and logging."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._logger = get_logger("battleship.engine")
        self._tracer = get_tracer("battleship.engine")
        self._game_span_cm = None
        self._game_span = None
        self._game_start_time: float | None = None
        self._game_id_counter = 0

    def setup_random(self) -> None:
        self._start_game_span()
        with self._tracer.start_as_current_span("battleship.engine.setup_random") as span:
            self._logger.info("Random setup started")
            super().setup_random()
            span.set_attribute("player1_ships", len(self.boards[Player.PLAYER1].ships))
            span.set_attribute("player2_ships", len(self.boards[Player.PLAYER2].ships))
            record_game_metric(
                "battleship_game_setup_total",
                1,
                {
                    "player1_ships": len(self.boards[Player.PLAYER1].ships),
                    "player2_ships": len(self.boards[Player.PLAYER2].ships),
                },
            )
            self._logger.info("Random setup finished")

    def make_move(self, player: Player, coord: Coordinate) -> tuple[CellState, Ship | None]:
        with self._tracer.start_as_current_span("battleship.engine.make_move") as span:
            span.set_attribute("game.id", self._game_id_counter)
            span.set_attribute("player", player.name)
            span.set_attribute("coord.row", coord.row)
            span.set_attribute("coord.col", coord.col)

            try:
                cell_state, ship = super().make_move(player, coord)
            except ValueError as exc:
                record_game_metric(
                    "battleship_game_invalid_moves_total",
                    1,
                    {"player": player.name, "reason": "invalid_move"},
                )
                span.record_exception(exc)
                span.set_attribute("error", True)
                self._logger.error("Invalid move from %s at (%d,%d): %s", player.name, coord.row, coord.col, exc)
                raise

            hit = cell_state is CellState.HIT
            span.set_attribute("shot_outcome", cell_state.name)
            span.set_attribute("hit", hit)
            span.set_attribute("sunk", bool(ship and ship.is_sunk()))

            record_game_metric("battleship_shots_total", 1, {"player": player.name})
            record_game_metric(
                "battleship_shots_by_result_total",
                1,
                {"player": player.name, "result": "hit" if hit else "miss"},
            )

            self._logger.info(
                "make_move player=%s coord=(%d,%d) outcome=%s",
                player.name,
                coord.row,
                coord.col,
                cell_state.name,
            )

            if self.phase is GamePhase.FINISHED and self.winner:
                span.set_attribute("winner", self.winner.name)
                self._finish_game()

            return cell_state, ship

    def _start_game_span(self) -> None:
        self._close_game_span()
        self._game_start_time = time.perf_counter()
        self._game_id_counter += 1
        self._game_span_cm = self._tracer.start_as_current_span("battleship.engine.game")
        self._game_span = self._game_span_cm.__enter__()
        self._game_span.set_attribute("game.id", self._game_id_counter)

    def _finish_game(self) -> None:
        duration = (time.perf_counter() - self._game_start_time) if self._game_start_time else 0.0
        total_turns = sum(len(board.shots) for board in self.boards.values())
        winner = self.winner.name if self.winner else "unknown"

        record_game_metric(
            "battleship_game_completed_total",
            1,
            {"winner": winner},
        )
        record_game_metric(
            "battleship_game_duration_seconds",
            duration,
            {"winner": winner},
        )

        with self._tracer.start_as_current_span("battleship.engine.game_complete") as span:
            span.set_attribute("game.id", self._game_id_counter)
            span.set_attribute("winner", winner)
            span.set_attribute("turns", total_turns)
            span.set_attribute("duration_ms", duration * 1000)

        if self._game_span is not None:
            self._game_span.set_attribute("winner", winner)
            self._game_span.set_attribute("turns", total_turns)
            self._game_span.set_attribute("duration_ms", duration * 1000)

        self._logger.info("Game finished. Winner=%s turns=%d duration_s=%.3f", winner, total_turns, duration)
        self._close_game_span()

    def _close_game_span(self) -> None:
        if self._game_span_cm is not None:
            self._game_span_cm.__exit__(None, None, None)
            self._game_span_cm = None
            self._game_span = None
