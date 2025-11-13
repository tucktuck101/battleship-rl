"""Instrumented Battleship game with telemetry hooks."""

from __future__ import annotations

from battleship.engine.board import CellState
from battleship.engine.game import BattleshipGame, GamePhase, Player
from battleship.engine.ship import Coordinate, Ship
from battleship.telemetry.logger import get_logger
from battleship.telemetry.metrics import record_game_metric
from battleship.telemetry.tracer import get_tracer


class InstrumentedBattleshipGame(BattleshipGame):
    """Wraps BattleshipGame with tracing, metrics, and logging."""

    def setup_random(self) -> None:
        tracer = get_tracer("battleship.engine")
        logger = get_logger("battleship.engine")
        with tracer.start_as_current_span("battleship.setup_random"):
            logger.info("Random setup started")
            super().setup_random()
            record_game_metric("game.setup.count", 1)
            logger.info("Random setup finished")

    def make_move(self, player: Player, coord: Coordinate) -> tuple[CellState, Ship | None]:
        tracer = get_tracer("battleship.engine")
        logger = get_logger("battleship.engine")
        with tracer.start_as_current_span("battleship.make_move") as span:
            span.set_attribute("player", player.name)
            span.set_attribute("coord.row", coord.row)
            span.set_attribute("coord.col", coord.col)

            cell_state, ship = super().make_move(player, coord)
            hit = cell_state is CellState.HIT
            span.set_attribute("shot_outcome", cell_state.name)
            span.set_attribute("hit", hit)
            span.set_attribute("sunk", bool(ship and ship.is_sunk()))

            record_game_metric("game.shots_total", 1, {"player": player.name})
            if hit:
                record_game_metric("game.hits_total", 1, {"player": player.name})
            else:
                record_game_metric("game.misses_total", 1, {"player": player.name})

            logger.info(
                "make_move player=%s coord=(%d,%d) outcome=%s",
                player.name,
                coord.row,
                coord.col,
                cell_state.name,
            )

            if self.phase is GamePhase.FINISHED and self.winner:
                record_game_metric("game.completed.count", 1, {"winner": self.winner.name})
                span.set_attribute("winner", self.winner.name)
                logger.info("Game finished. Winner=%s", self.winner.name)

            return cell_state, ship
