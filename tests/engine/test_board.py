"""Tests for the Board mechanics."""

import pytest
from battleship.engine.board import Board, CellState
from battleship.engine.ship import Coordinate, Orientation, Ship, ShipType


def test_board_shot_tracking() -> None:
    board = Board()
    ship = Ship(ShipType.DESTROYER, Coordinate(0, 0), Orientation.HORIZONTAL)
    assert board.place_ship(ship) is True

    hit_state, hit_ship = board.receive_shot(Coordinate(0, 0))
    assert hit_state is CellState.HIT
    assert hit_ship is ship
    assert not board.all_ships_sunk()

    miss_state, miss_ship = board.receive_shot(Coordinate(5, 5))
    assert miss_state is CellState.MISS
    assert miss_ship is None

    with pytest.raises(ValueError):
        board.receive_shot(Coordinate(0, 0))

    board.receive_shot(Coordinate(0, 1))
    assert board.all_ships_sunk()
