Battleship Game Rules for Engine Implementation
This document defines the exact rules for a standard Battleship game. These rules must be followed when implementing the game engine. The aim is to create a consistent and fair version of Battleship that matches the widely accepted tabletop game.
1. Game Components
Board: Each player has two 10 × 10 grids – one for placing their own ships and one for tracking shots fired at the opponent
officialgamerules.org
. Coordinates are typically labelled with letters for rows (A–J) and numbers for columns (1–10).
Fleet: Each player has a fleet of five ships
officialgamerules.org
. The ship types and their lengths (number of contiguous squares) are:
Carrier – length 5
officialgamerules.org
Battleship – length 4
officialgamerules.org
Cruiser – length 3
officialgamerules.org
Submarine – length 3
officialgamerules.org
Destroyer – length 2
officialgamerules.org
Markers: In the physical game, coloured pegs mark hits and misses
officialgamerules.org
. In software, the board state should record whether a cell contains a ship segment, a hit, a miss or remains unknown.
2. Setup
Ship Placement
Each player must place all five ships on their 10 × 10 grid before play starts. Ships may be placed horizontally or vertically, but not diagonally
officialgamerules.org
.
Ships must fit entirely within the boundaries of the grid and cannot overlap each other
officialgamerules.org
.
A ship may touch another ship at its ends or sides (adjacency), but no ship segments may occupy the same cell. Diagonal contact is allowed only if you choose to permit touching (house rule); by default, touching is allowed but overlapping is not.
Ship placement must be hidden from the opponent. The game engine should therefore maintain separate internal boards for each player and never reveal the opponent’s ship locations.
Initial Turn
Decide randomly (e.g. coin flip) which player goes first. The first player is typically called Player 0 and the opponent is Player 1. The game engine should allow deterministic seeding for reproducible games.
3. Gameplay
Players take turns calling out coordinates to attack the opponent’s ships
officialgamerules.org
. A turn consists of selecting a single cell on the opponent’s grid and announcing the coordinates.
Valid Shots
Only one shot is allowed per turn (the salvo variant with multiple shots is not part of the standard rules). Each shot targets exactly one cell on the opponent’s 10 × 10 grid.
The chosen coordinate must be within the bounds of the board (A–J and 1–10) and must not have been targeted previously. Attempting to shoot an already‑targeted cell is an invalid move. The engine should reject such moves or treat them as a miss with no effect.
Hit or Miss
After a shot is declared, the opponent checks their grid and announces whether the shot is a hit or a miss
officialgamerules.org
.
If the shot hits a ship segment, the engine should mark that cell as a hit and update the internal state of the ship. If the shot misses, mark the cell as a miss.
The shooting player updates their tracking grid accordingly (in the engine, maintain a separate view for each player showing hits and misses).
Sinking Ships
A ship is sunk when all of its segments have been hit
officialgamerules.org
. When this happens, the opponent must announce which ship was sunk
officialgamerules.org
.
Until a ship is sunk, the opponent only announces “hit” or “miss”; they do not reveal the type of ship that was hit
officialgamerules.org
.
After a ship is sunk, further shots at any of its cells are considered invalid because those cells are already hit.
Alternating Turns
Turns strictly alternate regardless of whether a shot is a hit or miss
officialgamerules.org
. The only exception is in advanced variants like “Salvo,” which are not part of the standard rules.
4. End of the Game
The game continues in alternating turns until one player has sunk all five of their opponent’s ships
officialgamerules.org
. The first player to sink all of their opponent’s ships is the winner
officialgamerules.org
. If both players sink each other’s last ship on the same turn (possible only in variants where players fire simultaneously), the game is a draw; however, in standard alternating play this situation does not occur because turns alternate.
5. Invalid Moves and Error Handling
Out‑of‑bounds shots: The engine must reject any coordinates outside the 10 × 10 grid. Do not change the game state on invalid input.
Repeated shots: Shots at previously targeted coordinates should be rejected or treated as a no‑op. The engine should prompt the player to choose a new coordinate.
Incorrect ship placement: If ships overlap or extend beyond the board during setup, the engine must detect this and prevent the game from starting until placement is corrected.
6. Optional Variants (Not Included by Default)
The following variants are not part of the standard rules but may be implemented as optional extensions after the core engine is complete:
Salvo: Each player fires multiple shots per turn equal to the number of unsunk ships they have remaining
officialgamerules.org
.
Special Weapons: Allow special attacks such as air strikes or torpedoes
officialgamerules.org
.
Fog of War: Players do not announce the type of ship hit; only whether the shot was a hit or miss
officialgamerules.org
.
These variants should be implemented separately and controlled by configuration options, so that the default game conforms strictly to the standard rules described above.
7. Implementation Notes
Although this document focuses on the rules rather than code, the following guidelines should help when designing the game engine:
Represent the board as a 2‑D data structure (e.g., a list of lists) where each cell can be empty, contain a reference to a ship, or record a hit/miss.
Represent ships as objects or records with fields: type, length, orientation, start_position, and a set of hit_positions to track hits.
Maintain separate state for each player: the placement board, the tracking board for shots fired, and the fleet (with ship states).
Provide deterministic random placement routines that respect the placement rules. Allow seeding the random number generator for reproducible games.
Validate all input (ship placement, shot coordinates) and handle invalid moves gracefully.
Ensure the engine is deterministic and reproducible: given the same initial seed and sequence of actions, the game outcome should be identical.
These rules and guidelines ensure that the Battleship game engine behaves consistently with the traditional board game, providing a robust foundation for further AI and user interface development.
