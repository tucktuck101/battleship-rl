"""Single-player board management for the Battleship engine."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum

from battleship.telemetry import get_meter, get_tracer

from .ship import Coordinate, Orientation, Ship, ShipType

logger = logging.getLogger(__name__)
tracer = get_tracer("battleship.engine.board")
meter = get_meter("battleship.engine.board")

PLACEMENT_COUNTER = meter.create_counter(
    "battleship_engine_ship_placements",
    unit="1",
    description="Number of attempted ship placements",
)

SHOT_COUNTER = meter.create_counter(
    "battleship_engine_shots",
    unit="1",
    description="Shots received by a board",
)


class CellState(Enum):
    """State of a board cell from the perspective of shots taken."""

    UNKNOWN = "unknown"
    MISS = "miss"
    HIT = "hit"


@dataclass
class Board:
    """Represents a player's 10×10 board and fleet of ships."""

    size: int = 10
    ships: list[Ship] = field(default_factory=list)
    shots: dict[Coordinate, CellState] = field(default_factory=dict)
    allow_adjacent: bool = True
    owner: str = "unknown"

    def is_valid_coordinate(self, coord: Coordinate) -> bool:
        """Check whether a coordinate lies inside the board boundaries."""
        return 0 <= coord.row < self.size and 0 <= coord.col < self.size

    def can_place_ship(self, ship: Ship) -> bool:
        """Determine whether a ship can be placed without violating rules."""
        coords = ship.coordinates()
        if not all(self.is_valid_coordinate(coord) for coord in coords):
            return False

        for existing in self.ships:
            if ship.overlaps(existing):
                return False

        if not self.allow_adjacent:
            occupied = self._occupied_coordinates()
            forbidden = self._adjacent_coordinates(occupied)
            if any(coord in forbidden for coord in coords):
                return False

        return True

    def place_ship(self, ship: Ship) -> bool:
        """Add ship to the board if placement is valid."""
        with tracer.start_as_current_span("board.place_ship") as span:
            span.set_attribute("ship.type", ship.ship_type.name)
            span.set_attribute("ship.length", ship.ship_type.length)
            span.set_attribute("ship.start.row", ship.start.row)
            span.set_attribute("ship.start.col", ship.start.col)
            span.set_attribute("board.owner", self.owner)
            if self.can_place_ship(ship):
                self.ships.append(ship)
                PLACEMENT_COUNTER.add(1, attributes={"result": "success", "owner": self.owner})
                logger.info(
                    "ship_placed",
                    extra={
                        "owner": self.owner,
                        "ship_type": ship.ship_type.name,
                        "orientation": ship.orientation.name,
                        "row": ship.start.row,
                        "col": ship.start.col,
                    },
                )
                return True
            PLACEMENT_COUNTER.add(1, attributes={"result": "failed", "owner": self.owner})
            logger.warning(
                "ship_placement_failed",
                extra={
                    "owner": self.owner,
                    "ship_type": ship.ship_type.name,
                    "orientation": ship.orientation.name,
                    "row": ship.start.row,
                    "col": ship.start.col,
                },
            )
            return False

    def receive_shot(self, coord: Coordinate) -> tuple[CellState, Ship | None]:
        """Register a shot at this board and return its outcome."""
        with tracer.start_as_current_span("board.receive_shot") as span:
            span.set_attribute("shot.row", coord.row)
            span.set_attribute("shot.col", coord.col)
            span.set_attribute("board.owner", self.owner)
            if not self.is_valid_coordinate(coord):
                logger.error(
                    "shot_out_of_bounds",
                    extra={"row": coord.row, "col": coord.col, "owner": self.owner},
                )
                raise ValueError("Shot out of bounds.")
            if coord in self.shots:
                logger.error(
                    "shot_duplicate",
                    extra={"row": coord.row, "col": coord.col, "owner": self.owner},
                )
                raise ValueError("Cell has already been targeted.")

            for ship in self.ships:
                if ship.hit(coord):
                    self.shots[coord] = CellState.HIT
                    span.set_attribute("shot.outcome", "hit")
                    SHOT_COUNTER.add(1, attributes={"outcome": "hit", "owner": self.owner})
                    logger.info(
                        "shot_hit",
                        extra={
                            "row": coord.row,
                            "col": coord.col,
                            "ship_type": ship.ship_type.name,
                            "owner": self.owner,
                        },
                    )
                    return CellState.HIT, ship

            self.shots[coord] = CellState.MISS
            span.set_attribute("shot.outcome", "miss")
            SHOT_COUNTER.add(1, attributes={"outcome": "miss", "owner": self.owner})
            logger.info(
                "shot_miss", extra={"row": coord.row, "col": coord.col, "owner": self.owner}
            )
            return CellState.MISS, None

    def get_cell_state(self, coord: Coordinate) -> CellState:
        """Return the state of a cell after shots have been taken."""
        return self.shots.get(coord, CellState.UNKNOWN)

    def all_ships_sunk(self) -> bool:
        """Check whether the player has any surviving ships."""
        return all(ship.is_sunk() for ship in self.ships)

    def random_placement(self, rng: random.Random) -> None:
        """Randomly place one ship of each type on the board."""
        with tracer.start_as_current_span("board.random_placement") as span:
            span.set_attribute("board.owner", self.owner)
            self.ships.clear()
            self.shots.clear()
            for ship_type in ShipType:
                placed = False
                attempts = 0
                while not placed:
                    orientation = rng.choice(list(Orientation))
                    start_row = rng.randrange(self.size)
                    start_col = rng.randrange(self.size)
                    candidate = Ship(ship_type, Coordinate(start_row, start_col), orientation)
                    placed = self.place_ship(candidate)
                    attempts += 1
                logger.debug(
                    "random_ship_placed",
                    extra={"ship_type": ship_type.name, "attempts": attempts, "owner": self.owner},
                )

    def _occupied_coordinates(self) -> set[Coordinate]:
        coords: set[Coordinate] = set()
        for ship in self.ships:
            coords.update(ship.coordinates())
        return coords

    def _adjacent_coordinates(self, coords: set[Coordinate]) -> set[Coordinate]:
        """Return the 8-neighbourhood (plus the cell itself) for each coordinate."""
        adjacent: set[Coordinate] = set(coords)
        for coord in coords:
            for delta_row in (-1, 0, 1):
                for delta_col in (-1, 0, 1):
                    if delta_row == 0 and delta_col == 0:
                        continue
                    neighbour = Coordinate(coord.row + delta_row, coord.col + delta_col)
                    if not self.is_valid_coordinate(neighbour):
                        continue
                    adjacent.add(neighbour)
        return adjacent
