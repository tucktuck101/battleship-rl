"""Ship domain model for the Battleship engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Coordinate:
    """Immutable board coordinate."""

    row: int
    col: int


class Orientation(Enum):
    """Allowed ship orientations."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class ShipType(Enum):
    """All supported ship classes and their lengths."""

    CARRIER = 5
    BATTLESHIP = 4
    CRUISER = 3
    SUBMARINE = 3
    DESTROYER = 2

    @property
    def length(self) -> int:
        """Return the number of contiguous cells the ship occupies."""
        return self.value


@dataclass
class Ship:
    """Represents a single ship instance on the board."""

    ship_type: ShipType
    start: Coordinate
    orientation: Orientation
    hits: set[Coordinate] = field(init=False)
    _coordinates: tuple[Coordinate, ...] = field(init=False, repr=False)
    _coordinate_set: set[Coordinate] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.hits = set()
        coords: list[Coordinate] = []
        for offset in range(self.ship_type.length):
            if self.orientation is Orientation.HORIZONTAL:
                coords.append(Coordinate(self.start.row, self.start.col + offset))
            else:
                coords.append(Coordinate(self.start.row + offset, self.start.col))
        self._coordinates = tuple(coords)
        self._coordinate_set = set(coords)

    def coordinates(self) -> list[Coordinate]:
        """Return the ordered list of coordinates occupied by this ship."""
        return list(self._coordinates)

    def is_sunk(self) -> bool:
        """Determine whether every coordinate belonging to the ship has been hit."""
        return self._coordinate_set.issubset(self.hits)

    def hit(self, coord: Coordinate) -> bool:
        """Record a hit if the coordinate belongs to this ship."""
        if coord not in self._coordinate_set:
            return False
        if coord in self.hits:
            return False
        self.hits.add(coord)
        return True

    def overlaps(self, other: Ship) -> bool:
        """Return True if any coordinate overlaps with another ship."""
        return bool(self._coordinate_set & other._coordinate_set)
