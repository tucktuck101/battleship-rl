"""Tests for the Board mechanics."""

import random

import pytest
from battleship.engine.board import Board, CellState
from battleship.engine.ship import Coordinate, Orientation, Ship, ShipType


def test_board_shot_tracking() -> None:
    board = Board()
    ship = Ship(ShipType.DESTROYER, Coordinate(0, 0), Orientation.HORIZONTAL)
    board.place_ship(ship)

    hit_state, hit_ship = board.receive_shot(Coordinate(0, 0))
    assert hit_state is CellState.HIT
    assert hit_ship is ship
    assert not board.all_ships_sunk()

    miss_state, miss_ship = board.receive_shot(Coordinate(5, 5))
    assert miss_state is CellState.MISS
    assert miss_ship is None

    with pytest.raises(ValueError):
        board.receive_shot(Coordinate(0, 0))

    with pytest.raises(ValueError):
        board.receive_shot(Coordinate(11, 11))

    board.receive_shot(Coordinate(0, 1))
    assert board.all_ships_sunk()


def test_ship_placement_rejects_overlap_and_bounds() -> None:
    board = Board()
    horizontal = Ship(ShipType.CRUISER, Coordinate(0, 0), Orientation.HORIZONTAL)
    board.place_ship(horizontal)

    overlapping = Ship(ShipType.DESTROYER, Coordinate(0, 1), Orientation.VERTICAL)
    with pytest.raises(ValueError):
        board.place_ship(overlapping)

    out_of_bounds = Ship(ShipType.DESTROYER, Coordinate(9, 9), Orientation.HORIZONTAL)
    with pytest.raises(ValueError):
        board.place_ship(out_of_bounds)


def test_ship_placement_respects_adjacency_rule() -> None:
    board = Board(allow_adjacent=False)
    first = Ship(ShipType.SUBMARINE, Coordinate(3, 3), Orientation.VERTICAL)
    board.place_ship(first)

    touching = Ship(ShipType.DESTROYER, Coordinate(2, 3), Orientation.HORIZONTAL)
    with pytest.raises(ValueError):
        board.place_ship(touching)


def test_random_placement_populates_full_fleet_without_overlap() -> None:
    board = Board()
    board.random_placement(rng=random.Random(123))
    assert len(board.ships) == len(ShipType)
    coords = [coord for ship in board.ships for coord in ship.coordinates()]
    assert len(coords) == len(set(coords)), "Ships should not overlap"


def test_get_cell_state_defaults_to_unknown() -> None:
    board = Board()
    state = board.get_cell_state(Coordinate(4, 4))
    assert state is CellState.UNKNOWN
