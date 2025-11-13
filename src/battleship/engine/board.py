"""Single-player board management for the Battleship engine."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from .ship import Coordinate, Orientation, Ship, ShipType


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
        if self.can_place_ship(ship):
            self.ships.append(ship)
            return True
        return False

    def receive_shot(self, coord: Coordinate) -> tuple[CellState, Ship | None]:
        """Register a shot at this board and return its outcome."""
        if not self.is_valid_coordinate(coord):
            raise ValueError("Shot out of bounds.")
        if coord in self.shots:
            raise ValueError("Cell has already been targeted.")

        for ship in self.ships:
            if ship.hit(coord):
                self.shots[coord] = CellState.HIT
                return CellState.HIT, ship

        self.shots[coord] = CellState.MISS
        return CellState.MISS, None

    def get_cell_state(self, coord: Coordinate) -> CellState:
        """Return the state of a cell after shots have been taken."""
        return self.shots.get(coord, CellState.UNKNOWN)

    def all_ships_sunk(self) -> bool:
        """Check whether the player has any surviving ships."""
        return all(ship.is_sunk() for ship in self.ships)

    def random_placement(self, rng: random.Random) -> None:
        """Randomly place one ship of each type on the board."""
        self.ships.clear()
        self.shots.clear()
        for ship_type in ShipType:
            placed = False
            while not placed:
                orientation = rng.choice(list(Orientation))
                start_row = rng.randrange(self.size)
                start_col = rng.randrange(self.size)
                candidate = Ship(ship_type, Coordinate(start_row, start_col), orientation)
                placed = self.place_ship(candidate)

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
