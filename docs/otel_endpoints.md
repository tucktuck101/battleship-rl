# OpenTelemetry Reference

Central list of the telemetry signals emitted by the Battleship RL stack. Use this as a lookup table when wiring Grafana dashboards, Loki queries, or trace searches.

## Metrics

| Metric name | Type | Emitted by | Description / when it changes | Useful attributes |
|-------------|------|------------|--------------------------------|-------------------|
| `battleship_engine_ship_placements` | Counter | `src/battleship/engine/board.py` | Incremented every time a board tries to place a ship (counts both manual and random placement attempts). | `result` (`success`/`failed`), `owner` (`player1`, `player2`, `opponent`, etc.) |
| `battleship_engine_shots` | Counter | `src/battleship/engine/board.py` | Counts every shot received by a board. | `outcome` (`hit`/`miss`), `owner` |
| `battleship_engine_moves` | Counter | `src/battleship/engine/game.py` | Increments after each validated turn processed by `BattleshipGame.make_move`. | `result` (cell state), `player` |
| `battleship_episode_reward` | Histogram | `Trainer` in `src/battleship/ai/training.py` | Records total reward per training episode. | – |
| `battleship_episode_mean_loss` | Histogram | `Trainer` | Records the mean loss value gathered during a training episode. | – |
| `battleship_eval_win_rate` | Histogram | `Trainer` | Records win rate observed during evaluation sweeps. | – |
| `agent.action_latency_ms` | Counter | `InstrumentedDQNAgent` (`src/battleship/ai/instrumented_agent.py`) | Adds the elapsed milliseconds for every `select_action` call. | – |
| `agent.training_steps` | Counter | `InstrumentedDQNAgent` | Bumps once per `train_step`. | – |
| `agent.training_latency_ms` | Counter | `InstrumentedDQNAgent` | Adds the time spent inside a `train_step`. | – |
| `agent.training_loss` | Counter | `InstrumentedDQNAgent` | Adds the numeric loss (if available) on each training update so trending is possible. | – |
| `game.setup.count` | Counter | `InstrumentedBattleshipGame` (`src/battleship/engine/instrumented_game.py`) | Incremented whenever a random setup finishes. | – |
| `game.shots_total` | Counter | `InstrumentedBattleshipGame` | Counts every call to `make_move`. | `player` |
| `game.hits_total` | Counter | `InstrumentedBattleshipGame` | Subset of `game.shots_total` when the outcome is a hit. | `player` |
| `game.misses_total` | Counter | `InstrumentedBattleshipGame` | Subset of `game.shots_total` when the outcome is a miss. | `player` |
| `game.completed.count` | Counter | `InstrumentedBattleshipGame` | Incremented when a match ends. | `winner` |

> All metrics inherit the `service.name=battleship-trainer` (and namespace `ml`) resource attributes configured in `battleship.telemetry`.

## Logs

All logs automatically include the current OTEL trace/span identifiers (via `LoggingInstrumentor`). The key structured log events you can filter in Loki are grouped below.

- **Engine board (`src/battleship/engine/board.py`)**
  - `ship_placed`, `ship_placement_failed` – placement attempts with `owner`, `ship_type`, `orientation`, `row`, `col`.
  - `shot_hit`, `shot_miss`, `shot_out_of_bounds`, `shot_duplicate` – fired when shots are processed.
  - `random_ship_placed` – debug log after each RNG placement, includes attempt counts.
- **Engine game (`src/battleship/engine/game.py`)**
  - `game_random_placement`, `game_setup_random_complete` – lifecycle of RNG setup.
  - `move_rejected_game_not_in_progress`, `move_rejected_wrong_player` – guards against illegal turn orders.
  - `game_finished` – announces the winner and finishing player.
- **Environment (`src/battleship/ai/environment.py`)**
  - `env_reset`, `env_phase_transition` – high-level state changes.
  - `invalid_action` – emitted for any illegal placement or firing action; includes `phase`, `reason`, `actor`, and sometimes coordinates.
  - `player_placement_complete`, `opponent_manual_placement_complete`, `opponent_manual_placement_fallback` – track placement phase progress.
- **Trainer (`src/battleship/ai/training.py`)**
  - `trainer_initialised` – config summary.
  - `train_episode` – reward/steps/loss per episode.
  - `evaluate_agent` – evaluation aggregates (also logged inside `scripts/auto_train_pipeline.py` as `phase_*` events).
- **Pipeline (`scripts/auto_train_pipeline.py`)**
  - `phase_start`, `phase_episode`, `phase_epoch_eval`, `phase_criteria_met`, `phase_complete`, etc. – describe adaptive phase transitions during automated training runs.
- **Instrumented agent/game helpers**
  - `select_action …`, `train_step …`, and `make_move …` logs expose low-level insight when the instrumented wrappers are in use.

Each logger inherits OTEL metadata, so filtering by `owner`, `actor`, or `phase` in Loki will identify which player/agent generated a warning.

## Traces

Traces wrap the major control-flow segments so Tempo (or any OTLP trace backend) can stitch together full-episode execution. All spans share the `service.name=battleship-trainer` resource attribute unless otherwise overridden.

| Span name | Defined in | Notes |
|-----------|------------|-------|
| `board.place_ship` | `src/battleship/engine/board.py` | Captures validations and placement attempts; records ship metadata and `board.owner`. |
| `board.receive_shot` | `src/battleship/engine/board.py` | Encloses all hit/miss calculations for a single incoming shot. |
| `board.random_placement` | `src/battleship/engine/board.py` | Wraps the random fleet generation loop. |
| `game.setup_random` | `src/battleship/engine/game.py` | Covers end-to-end game setup across both boards. |
| `game.make_move` | `src/battleship/engine/game.py` | Spans every validated turn, tagging coordinates, outcome, and winner transitions. |
| `battleship.setup_random`, `battleship.make_move` | `src/battleship/engine/instrumented_game.py` | Additional spans when using the instrumented game wrapper (delegates to base implementation but provides dedicated tracer namespace). |
| `agent.select_action`, `agent.train_step` | `src/battleship/ai/instrumented_agent.py` | Span per inference or optimisation step when the instrumented agent is used. |
| `train_episode` | `src/battleship/ai/training.py` | Wraps the full Gym episode (reset → steps) while recording reward/loss attributes. |
| `evaluate_agent` | `src/battleship/ai/training.py` | Wraps evaluation sweeps; attributes include win rate and episode lengths. |
| `pipeline.phase` | `scripts/auto_train_pipeline.py` | Top-level span for each adaptive phase executed by `auto_train_pipeline.py`. |

Because logging is instrumented, every log written inside these spans includes the trace/span IDs, making it easy to pivot between traces, logs, and metrics across the entire training environment (including engine modules under `src/` and orchestration scripts under `scripts/`).
