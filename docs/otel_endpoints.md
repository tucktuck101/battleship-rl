# OpenTelemetry Reference

Authoritative guide to the telemetry design used across Battleship RL. Use this
to understand metric/span naming, attribute conventions, and how to wire
exporters via `TelemetryConfig`.

## Naming & Attribute Conventions

- **Namespaces**
  - Spans: `battleship.engine.*`, `battleship.env.*`, `battleship.agent.*`, `battleship.ai.*`.
  - Metrics: all prefixed with `battleship_`.
  - Loggers: module-specific (e.g., `battleship.engine`, `battleship.env`).
- **Common resource attributes**: `service.name`, `service.namespace`, plus any
  values defined in `OTEL_RESOURCE_ATTRIBUTES`. Default service names:
  - Engine/env instrumentation: `battleship` / namespace `game`.
  - Trainer/pipeline: `battleship-trainer` / namespace `ml`.
- **Span attributes**
  - Engine: `game.id`, `player`, `coord.row`, `coord.col`, `shot_outcome`,
    `hit`, `sunk`.
  - Environment: `episode_id`, `phase`, `action_index`, `reward`,
    `reward_type`, `invalid_action`, `terminated`, `truncated`.
  - Agent: `epsilon`, `mode` (`explore|exploit`), `buffer_size`, `batch_size`.
- All attributes/labels are deliberately low-cardinality; avoid coordinates or
  IDs in metric labels beyond the bounded ones listed above.

## Metrics

| Metric name | Type | Emitted by | Description / when it changes | Attributes |
|-------------|------|------------|--------------------------------|------------|
| `battleship_game_setup_total` | Counter | Instrumented game | Random setup completed | `player1_ships`, `player2_ships` |
| `battleship_game_completed_total` | Counter | Instrumented game | Match finished | `winner` |
| `battleship_game_duration_seconds` | Histogram | Instrumented game | Setup→finish duration | `winner` |
| `battleship_shots_total` | Counter | Instrumented game | Every move | `player` |
| `battleship_shots_by_result_total` | Counter | Instrumented game | Same as above but labelled by result | `player`, `result=hit|miss` |
| `battleship_game_invalid_moves_total` | Counter | Instrumented game | Invalid moves rejected | `player`, `reason` |
| `battleship_env_reset_total` | Counter | `BattleshipEnv.reset` | Gym reset invoked | – |
| `battleship_env_reset_latency_ms` | Histogram | `BattleshipEnv.reset` | Reset latency | – |
| `battleship_env_actions_total` | Counter | `BattleshipEnv.step` | Placement + firing actions | `phase=placement|firing`, `result=valid|invalid` |
| `battleship_env_step_latency_ms` | Histogram | `BattleshipEnv.step` | Runtime per step | `phase` |
| `battleship_env_rewards_total` | Counter | `BattleshipEnv.step` | Positive/zero rewards per step | `phase`, `type=hit|miss|placement_complete|invalid|terminal` |
| `battleship_env_negative_rewards_total` | Counter | `BattleshipEnv.step` | Absolute magnitude of negative rewards | `phase`, `type` |
| `battleship_env_hits_total` / `battleship_env_misses_total` | Counter | `BattleshipEnv.step` | Subset of actions | `phase` |
| `battleship_env_invalid_actions_total` | Counter | `BattleshipEnv.step` | Invalid placement/firing attempts | `phase` |
| `battleship_env_episode_completed_total` | Counter | `BattleshipEnv.step` | Episode terminates or truncates | `result=win|loss|truncated` |
| `battleship_agent_actions_total` | Counter | Instrumented DQN agent | Chosen actions | `mode=explore|exploit` |
| `battleship_agent_action_latency_ms` | Histogram | Instrumented DQN agent | `select_action` latency | `mode` |
| `battleship_agent_epsilon` | Counter | Instrumented DQN agent | Current epsilon (write latest value) | – |
| `battleship_agent_training_steps_total` | Counter | Instrumented DQN agent | `train_step` invocations | – |
| `battleship_agent_training_latency_ms` | Histogram | Instrumented DQN agent | Training step duration | – |
| `battleship_agent_training_loss` | Counter | Instrumented DQN agent | Loss per update | – |
| `battleship_episode_reward`, `battleship_episode_mean_loss`, `battleship_eval_win_rate` | Histogram | Trainer | Episode totals and evaluation stats | – |

> All metrics inherit the resource attributes configured via `TelemetryConfig`.

## Spans

| Span name | Source | Notes |
|-----------|--------|-------|
| `board.place_ship`, `board.receive_shot`, `board.random_placement` | `src/battleship/engine/board.py` | Low-level board operations |
| `battleship.engine.game` | `src/battleship/engine/instrumented_game.py` | Top-level span per match |
| `battleship.engine.setup_random`, `battleship.engine.make_move`, `battleship.engine.game_complete` | Instrumented game | Child spans covering setup, each move, and completion |
| `battleship.env.reset`, `battleship.env.step` | `src/battleship/ai/environment.py` | Child spans for Gym resets/steps; tags include reward type, validity, termination |
| `battleship.agent.select_action`, `battleship.agent.train_step` | `src/battleship/ai/instrumented_agent.py` | Inference/training spans containing epsilon/mode/buffer stats |
| `train_episode`, `evaluate_agent` | `src/battleship/ai/training.py` | Episode-level spans with reward/loss/win-rate attributes |
| `pipeline.phase` and derivatives | `scripts/auto_train_pipeline.py` | Adaptive training pipeline phases |

Every major log statement executes inside one of the spans above, so Tempo ↔ Loki
correlation uses the embedded trace/span IDs automatically.

## Logs

- Engine board: `ship_placed`, `ship_placement_failed`, `shot_hit`, `shot_miss`, `shot_out_of_bounds`, `shot_duplicate`, `random_ship_placed`.
- Engine game/instrumented game: `make_move …`, `game finished`, validation warnings.
- Environment: `env_reset`, `env_phase_transition`, `invalid_action`, `player_placement_complete`, `opponent_manual_placement_*`.
- Trainer/pipeline: `trainer_initialised`, `train_episode`, `evaluate_agent`, `phase_start`, `phase_complete`, etc.
- Agent: `select_action` and `train_step` logs show epsilon, action, exploratory flag, loss.

All logs inherit OTEL context (trace/span IDs) so Loki queries can pivot directly to Tempo traces.

## Exporter Wiring

`TelemetryConfig` reads environment variables and toggles tracing/metrics/logging.
Common settings:

| Variable | Purpose |
|----------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` or signal-specific `OTEL_EXPORTER_OTLP_{TRACES|METRICS|LOGS}_ENDPOINT` | Enables exporters and sets the endpoint |
| `BATTLESHIP_ENABLE_TRACING`, `BATTLESHIP_ENABLE_METRICS`, `BATTLESHIP_ENABLE_LOGGING` | Force-enable/disable individual signals |
| `OTEL_SERVICE_NAME`, `OTEL_SERVICE_NAMESPACE` | Override resource metadata |
| `OTEL_RESOURCE_ATTRIBUTES` | Extra resource attributes (comma-separated `key=value`) |

Usage:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="battleship-trainer"
export BATTLESHIP_ENABLE_TRACING=1
export BATTLESHIP_ENABLE_METRICS=1
export BATTLESHIP_ENABLE_LOGGING=1

PYTHONPATH=src python -m battleship.ai.training ...
```

Any component can also instantiate a config directly:

```python
from battleship.telemetry import TelemetryConfig, init_telemetry

config = TelemetryConfig.from_env(service_name="battleship-ui")
init_telemetry(config)
```

The helpers (`get_tracer`, `get_meter`, `get_logger`, `record_game_metric`,
`load_telemetry_config`) encapsulate exporter wiring so the rest of the codebase
never reaches into OTLP clients directly.
