# BattleshipEnv – Action & Observation Spaces

`BattleshipEnv` wraps the deterministic Battleship engine and exposes a
Gymnasium-compatible interface defined in `battleship.ai.environment`. This
doc captures the exact observation tensor layout, action encoding, and reward /
termination guarantees so agents can interoperate without reverse-engineering
the environment code.

## Observation Space

- Gymnasium space: `Box(low=0.0, high=1.0, shape=(C, 10, 10), dtype=float32)`
- Base channels (`C = 6` when `allow_agent_placement=False`)

| Channel | Meaning | Values |
| --- | --- | --- |
| 0 | Player fleet occupancy (1 = ship segment) | {0, 1} |
| 1 | Player ship damage map (1 = ship segment that has been hit) | {0, 1} |
| 2 | Cells the agent fired at on the opponent board | {0, 1} |
| 3 | Confirmed hits on the opponent board | {0, 1} |
| 4 | Coordinate of the opponent’s most recent shot (one-hot) | {0, 1} |
| 5 | Turn parity channel (`step_count % 2` broadcast over the grid) | {0, 1} |

### Placement Channels

When `allow_agent_placement=True`, the tensor gains `len(ShipType)` additional
channels that indicate whether each ship still needs to be placed. Every entry
in these planes is set to `1.0` while the ship is pending and `0.0` once placed.
A final channel indicates whether the environment is in the `placement` phase
(`1.0`) or firing phase (`0.0`). The overall channel count becomes
`BASE_NUM_CHANNELS + len(ShipType) + 1`.

### Validation

Observations are produced via `_build_observation_for_player` using the schema
above. The Gymnasium `Box` declaration ensures calls to
`env.observation_space.contains(obs)` pass without warnings for both placement
and firing phases, and regression tests in `tests/ai/test_environment.py`
assert shapes/dtypes explicitly.

## Action Space

- Gymnasium space: `Discrete(total_actions)`
- Default firing mode (`allow_agent_placement=False`):
  - `total_actions = 100` (10×10 grid)
  - Action index `i` decodes to row `i // 10`, column `i % 10`
- Placement-enabled mode:
  - `total_actions = 100 + len(ShipType) * 100 * len(Orientation)`
  - Segment after the first 100 indices encodes placement commands as:
    - Ship block = `(action - NUM_CELLS) // (NUM_CELLS * len(Orientation))`
    - Orientation sub-block and coordinate derived from the remainder.

At every reset/step call the `info` dict includes an `action_mask` array that
flags which discrete indices are currently legal. Placement phases expose only
placement indices, while firing phases expose only firing coordinates.

## Rewards & Termination

- Base reward shaping constants (see `environment.py`):
  - `HIT_REWARD = +0.1`, `MISS_PENALTY = -0.01`,
    `INVALID_ACTION_PENALTY = -0.1`
  - Optional bonuses for finishing placement (`+0.05`) or each successful
    placement action (`+0.01`)
  - Episode outcome rewards: win `+1.0`, loss `-1.0`
- Episodes terminate when the underlying `BattleshipGame` reaches
  `GamePhase.FINISHED` or when the hard `MAX_STEPS` limit (400) is reached,
  leading to a Gymnasium `truncated=True` signal.
- Determinism: passing identical RNG seeds to `BattleshipEnv` reproduces the
  same placements, observations, rewards, and terminal states. The test
  `test_deterministic_seeding` covers this contract.

## Gymnasium Registration

Importing `battleship.ai` registers the environment as
`"BattleshipEnv-v0"` so `gymnasium.make("BattleshipEnv-v0")` constructs an
instance with the default (random placement) configuration. Alternate setups
can still instantiate `BattleshipEnv` directly for additional keyword args.
