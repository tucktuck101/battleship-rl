# Battleship Rules – Engine Contract

This document defines the ruleset enforced by the deterministic engine and
referenced by the Gym environment, CLI, and UI surfaces. Each API that exposes
game state should link here so consumers share a single definition of setup,
turn sequencing, and edge-case handling.

## 1. Core Components

- **Board** – Each player owns a hidden 10×10 grid addressed as `(row, col)`
  where `row ∈ [0, 9]` and `col ∈ [0, 9]`. Clients may render row/column
  labels (e.g., A–J / 1–10) but the engine only uses integer coordinates.
- **Fleet** – Exactly five ships per player:
  - Carrier (length 5)
  - Battleship (length 4)
  - Cruiser (length 3)
  - Submarine (length 3)
  - Destroyer (length 2)
- **Cell States** – Every board cell may be `unknown`, `hit`, or `miss`
  depending on shot history.

## 2. Setup Phase

1. **Ship Placement**
   - Ships occupy consecutive cells horizontally or vertically; diagonal
     placement is forbidden.
   - Ship coordinates must lie entirely within the 10×10 board.
   - Ships may not overlap. When `allow_adjacent=False`, ships must also avoid
     sharing edges/corners (the engine enforces this by rejecting placement).
2. **Hidden Information**
   - Each player sees only their fleet locations and the shots they have fired.
     APIs must never expose the opponent’s fleet until a ship is sunk.
3. **Deterministic Seeding**
   - Random placement routines accept RNG seeds so scripted tests and training
     jobs can reproduce layouts. The CLI and Gym environment wire these seeds
     through to `BattleshipGame`.

## 3. Turn Order & Gameplay

1. **Alternating Turns**
   - Player 1 fires first by default. Players alternate exactly one shot per
     turn regardless of hit/miss outcomes (no salvo variant in the base rules).
2. **Valid Shots**
   - Coordinates must be on the board and have never been targeted before.
     Attempting to shoot the same cell twice raises a `ValueError`.
3. **Shot Resolution**
   - If a bullet lands on a ship coordinate, the engine marks that cell `hit`
     and tracks the ship’s damage. Otherwise the cell becomes `miss`.
   - When all coordinates for a ship have been hit the ship is considered sunk.
     `BattleshipGame` emits the ship reference so UIs can announce the sink.
4. **State Snapshots**
   - `BattleshipGame.get_state()` returns immutable snapshots of each board’s
     ship coordinates and shot map so observers can serialize the match.

## 4. Victory, Termination, and Edge Rules

- **Win Condition** – The first player to sink all five of the opponent’s
  ships wins. The engine sets `GamePhase.FINISHED` and `winner` accordingly.
- **Draws** – Standard alternating play cannot produce simultaneous wins;
  therefore the engine never emits a draw.
- **Invalid Input Handling**
  - Out-of-bounds shots raise `ValueError` and do not advance the turn.
  - Shots at previously targeted cells raise `ValueError`.
  - Ship placements that extend off the board, overlap, or violate adjacency
    (when disabled) raise `ValueError`.
- **Timeouts / Max Steps**
  - Gym environments enforce a hard `MAX_STEPS` cap (400) and return a
    `truncated` flag when exceeded. Engine-only workflows usually terminate
    naturally via the win condition but can also enforce similar guards.

## 5. Optional Variants (Future)

The baseline engine intentionally excludes common Battleship variants to keep
deterministic behavior predictable. Optional extensions should live behind
explicit feature flags:

- **Salvo mode** – Multiple shots per turn equal to remaining ships.
- **Special weapons** – Air strikes or depth charges that target regions.
- **Fog of war tweaks** – Alternative hit/miss reporting for UI-specific
  experiences.

Any variant must preserve compatibility with the default APIs by clearly
signaling the rule set in match metadata.

## 6. Implementation Guidance

- Maintain separate `Board` instances per player; never share mutable state.
- Use dataclasses (`Ship`, `Coordinate`, `GameState`) to produce serializable
  snapshots consumed by telemetry, Gym observations, and replay tooling.
- Guard every mutation method (`place_ship`, `receive_shot`, `make_move`)
  with deterministic error handling so regression tests can assert failure
  modes.
- Keep RNG usage encapsulated in `setup_random` and `Board.random_placement`
  so other flows remain deterministic given a fixed action sequence.

By adhering to these rules the Battleship engine, Gym environment, and user
interfaces remain consistent, reproducible, and easy to reason about.
