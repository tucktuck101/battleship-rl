"""High-level gameplay tests."""

import random

from battleship.engine.game import BattleshipGame, GamePhase, Player


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
