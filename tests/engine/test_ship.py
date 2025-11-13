"""Tests for Ship domain logic."""

from battleship.engine.ship import Coordinate, Orientation, Ship, ShipType


def test_ship_coordinates_horizontal() -> None:
    ship = Ship(ShipType.DESTROYER, Coordinate(0, 0), Orientation.HORIZONTAL)
    assert ship.coordinates() == [Coordinate(0, 0), Coordinate(0, 1)]


def test_ship_hit_and_sink() -> None:
    ship = Ship(ShipType.CRUISER, Coordinate(3, 3), Orientation.VERTICAL)
    for idx, coord in enumerate(ship.coordinates(), start=1):
        assert ship.hit(coord) is True
        assert ship.is_sunk() is (idx == ship.ship_type.length)
