"""Simple command-line driver for playing Battleship against a random AI."""

from __future__ import annotations

import argparse
import random
from typing import Sequence

from battleship.engine.board import Board, CellState
from battleship.engine.game import BattleshipGame, GamePhase, Player
from battleship.engine.ship import Coordinate, Orientation, Ship, ShipType

ROW_LABELS = "ABCDEFGHIJ"


def _coordinate_from_input(text: str) -> Coordinate:
    cleaned = text.strip().upper()
    if not cleaned:
        raise ValueError("Empty coordinate.")
    if cleaned[0].isalpha():
        if cleaned[0] not in ROW_LABELS:
            raise ValueError("Row must be between A and J.")
        row = ROW_LABELS.index(cleaned[0])
        try:
            col = int(cleaned[1:]) - 1
        except ValueError as exc:
            raise ValueError("Column must be a number between 1 and 10.") from exc
    else:
        parts = cleaned.split()
        if len(parts) != 2:
            raise ValueError("Use formats like A5 or '3 7'.")
        row, col = map(int, parts)
    if row not in range(10) or col not in range(10):
        raise ValueError("Coordinates must be within the 10x10 board.")
    return Coordinate(row, col)


def _ship_cells(ship: Ship) -> set[Coordinate]:
    return set(ship.coordinates())


def _format_board(board: Board, show_ships: bool) -> str:
    ship_cells: set[Coordinate] = set()
    if show_ships:
        for ship in board.ships:
            ship_cells.update(_ship_cells(ship))

    header = "    " + " ".join(f"{col+1:>2}" for col in range(board.size))
    rows = [header]
    for row in range(board.size):
        symbols = []
        for col in range(board.size):
            coord = Coordinate(row, col)
            state = board.get_cell_state(coord)
            if state is CellState.HIT:
                symbol = "X"
            elif state is CellState.MISS:
                symbol = "o"
            else:
                symbol = "S" if coord in ship_cells else "."
            symbols.append(f"{symbol:>2}")
        rows.append(f"{ROW_LABELS[row]} |" + " ".join(symbols))
    return "\n".join(rows)


def _prompt_for_coordinate(valid: Sequence[Coordinate]) -> Coordinate:
    valid_set = {coord for coord in valid}
    while True:
        raw = input("Enter target coordinate (e.g., A5) or 'q' to quit: ").strip()
        if raw.lower() == "q":
            raise SystemExit("Goodbye!")
        try:
            coord = _coordinate_from_input(raw)
        except ValueError as exc:
            print(f"Invalid input: {exc}")
            continue
        if coord not in valid_set:
            print("That cell has already been targeted. Choose another.")
            continue
        return coord


def _describe_shot(player: Player, coord: Coordinate, hit_ship: Ship | None) -> str:
    col_display = coord.col + 1
    label = f"{ROW_LABELS[coord.row]}{col_display}"
    outcome = "hit" if hit_ship else "miss"
    if hit_ship and hit_ship.is_sunk():
        outcome = f"sank the opponent's {hit_ship.ship_type.name.lower()}!"
    return f"{player.name} fired at {label}: {outcome}"


def _prompt_orientation(ship_type: ShipType) -> Orientation:
    while True:
        raw = (
            input(
                f"Place your {ship_type.name.title()} (length {ship_type.length}). Orientation [H/V]: "
            )
            .strip()
            .upper()
        )
        if raw in {"H", "HOR", "HORIZONTAL"}:
            return Orientation.HORIZONTAL
        if raw in {"V", "VER", "VERTICAL"}:
            return Orientation.VERTICAL
        print("Please enter H for horizontal or V for vertical.")


def _manual_ship_placement(board: Board) -> None:
    board.ships.clear()
    board.shots.clear()
    for ship_type in ShipType:
        while True:
            print("\nCurrent layout:")
            print(_format_board(board, show_ships=True))
            orientation = _prompt_orientation(ship_type)
            start_raw = input("Enter starting coordinate (e.g., A1): ")
            try:
                start = _coordinate_from_input(start_raw)
            except ValueError as exc:
                print(f"Invalid coordinate: {exc}")
                continue
            ship = Ship(ship_type, start, orientation)
            if board.can_place_ship(ship):
                board.place_ship(ship)
                break
            print("Ship cannot be placed there (out of bounds or overlaps). Try again.")


def _prompt_manual_setup() -> bool:
    while True:
        raw = input("Would you like to place your ships manually? [Y/n]: ").strip().lower()
        if raw in {"", "y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer with 'y' or 'n'.")


def play_game(seed: int | None = None) -> None:
    print("Welcome to Battleship!\n")
    rng = random.Random(seed)
    game = BattleshipGame(rng_seed=seed)
    player_board = game.boards[Player.PLAYER1]
    ai_board = game.boards[Player.PLAYER2]

    if _prompt_manual_setup():
        _manual_ship_placement(player_board)
    else:
        player_board.random_placement(rng)
        print("\nYour ships have been positioned automatically.")

    ai_board.random_placement(rng)
    game.phase = GamePhase.IN_PROGRESS
    game.current_player = Player.PLAYER1
    game.winner = None

    while game.phase is GamePhase.IN_PROGRESS:
        player = game.current_player
        opponent = player.opponent()
        player_board = game.boards[player]
        opponent_board = game.boards[opponent]

        if player is Player.PLAYER1:
            print("\nYour Board:")
            print(_format_board(player_board, show_ships=True))
            print("\nEnemy Waters:")
            print(_format_board(opponent_board, show_ships=False))

            valid_moves = game.valid_moves(player)
            coord = _prompt_for_coordinate(valid_moves)
            state, ship = game.make_move(player, coord)
            print(_describe_shot(player, coord, ship))
        else:
            valid_moves = game.valid_moves(player)
            coord = random.choice(valid_moves)
            state, ship = game.make_move(player, coord)
            print(_describe_shot(player, coord, ship))

    winner = game.winner
    if winner is Player.PLAYER1:
        print("\nCongratulations, you won!")
    else:
        print("\nThe AI won this time. Better luck next battle!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Play Battleship via the CLI.")
    parser.add_argument(
        "--seed", type=int, default=None, help="Optional RNG seed for reproducibility."
    )
    args = parser.parse_args()
    play_game(seed=args.seed)


if __name__ == "__main__":
    main()
