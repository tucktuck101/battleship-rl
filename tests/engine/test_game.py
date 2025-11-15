"""High-level gameplay tests."""

import random

import pytest

from battleship.engine.game import BattleshipGame, GamePhase, Player
from battleship.engine.ship import Coordinate, Orientation, Ship, ShipType


def test_game_flow() -> None:
    rng_seed = 42
    game = BattleshipGame(rng_seed=rng_seed)
    game.setup_random()

    seen_moves = set()
    while game.get_state().phase is not GamePhase.FINISHED:
        state = game.get_state()
        player = state.current_player
        valid_moves = game.valid_moves(player)
        assert valid_moves, "There should always be a valid move while game in progress."
        coord = random.choice(valid_moves)
        move_key = (player, coord)
        assert move_key not in seen_moves, "Duplicate move attempted."
        seen_moves.add(move_key)
        game.make_move(player, coord)

    final_state = game.get_state()
    assert final_state.winner is not None
    assert final_state.phase is GamePhase.FINISHED
    assert final_state.winner in {Player.PLAYER1, Player.PLAYER2}


def test_make_move_requires_in_progress_game() -> None:
    game = BattleshipGame()
    with pytest.raises(RuntimeError):
        game.make_move(Player.PLAYER1, Coordinate(0, 0))


def test_make_move_enforces_turn_order() -> None:
    game = BattleshipGame(rng_seed=1)
    game.setup_random()
    first_coord = game.valid_moves(Player.PLAYER1)[0]
    game.make_move(Player.PLAYER1, first_coord)

    with pytest.raises(RuntimeError):
        game.make_move(Player.PLAYER1, game.valid_moves(Player.PLAYER1)[0])


def test_valid_moves_empty_before_game_starts() -> None:
    game = BattleshipGame()
    assert game.valid_moves(Player.PLAYER1) == []


def test_game_detects_winner_once_all_ships_sunk() -> None:
    game = BattleshipGame()
    attacker = Player.PLAYER1
    defender = attacker.opponent()
    defender_board = game.boards[defender]
    defender_board.ships.clear()
    defender_board.shots.clear()
    ship = Ship(ShipType.DESTROYER, Coordinate(0, 0), Orientation.HORIZONTAL)
    defender_board.place_ship(ship)
    game.phase = GamePhase.IN_PROGRESS
    game.current_player = attacker

    for coord in ship.coordinates():
        game.make_move(attacker, coord)

    assert game.phase is GamePhase.FINISHED
    assert game.winner is attacker


def test_game_state_snapshot_reflects_shots_and_phase() -> None:
    game = BattleshipGame(rng_seed=5)
    game.setup_random()
    player = Player.PLAYER1
    target = game.valid_moves(player)[0]
    game.make_move(player, target)
    state = game.get_state()
    assert state.phase in {GamePhase.IN_PROGRESS, GamePhase.FINISHED}
    opponent_board = state.boards[player.opponent()]
    assert target in opponent_board.shots
