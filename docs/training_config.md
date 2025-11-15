# Training Configuration Reference

This guide centralizes the hyperparameters, CLI flags, and artifact
conventions used by `battleship.ai.training`. Keep it synchronized with
`TrainingConfig` so newcomers can reason about defaults without diving
into the code.

## Default Hyperparameters

| Field | Default | Description |
| --- | --- | --- |
| `num_episodes` | 200 | Total training iterations. |
| `max_steps_per_episode` | 500 | Hard cap per episode to avoid endless stalemates. |
| `eval_interval` | 20 | Episodes between evaluation runs. |
| `eval_episodes` | 5 | Evaluation episodes per checkpoint. |
| `gamma` | 0.99 | Discount factor applied inside `DQNAgent`. |
| `lr` | 1e-3 | Adam learning rate. |
| `batch_size` | 64 | Replay batch size. |
| `buffer_capacity` | 100_000 | Replay buffer capacity. |
| `min_buffer_size` | 1_000 | Samples required before training starts. |
| `epsilon_start` | 1.0 | Initial exploration rate. |
| `epsilon_end` | 0.05 | Minimum exploration rate. |
| `epsilon_decay` | 0.995 | Multiplicative decay applied per train step. |
| `target_update_interval` | 1_000 | Steps between target network syncs. |
| `env_seed` | 42 | Seed for `BattleshipEnv`. |
| `agent_seed` | 7 | Seed for numpy/torch RNG. |
| `save_dir` | `training_artifacts` | Location for checkpoints + metrics. |
| `opponent` | `random` | Opponent type (`random`, `self`, or `checkpoint`). |
| `opponent_checkpoint` | `None` | Path when `opponent="checkpoint"`. |
| `opponent_manual_placement` | `False` | Let opponent place ships manually. |
| `rollout_episodes` | `0` | Number of policy rollouts after evaluations. |
| `rollout_path` | `policy_rollouts.jsonl` | File (inside `save_dir`) for rollout summaries. |

## CLI Flags

The trainer exposes the following flags (see `python -m battleship.ai.training --help`):

| Flag | Description |
| --- | --- |
| `--episodes` | Override `num_episodes`. |
| `--save-dir` | Destination directory for artifacts. |
| `--opponent` | `random`, `self`, or path to checkpoint. |
| `--opponent-placement` | Enable opponent self-placement (`allow_opponent_placement`). |
| `--rollout-episodes` | Number of rollout episodes after each evaluation interval. |
| `--rollout-path` | JSONL file (relative to `save-dir`) for rollout summaries. |

All other hyperparameters currently require code edits or config injection
(e.g., `TrainingConfig(**json.load(...))`). When the CLI grows more flags,
mirror them here.

## Artifacts & Metrics

Every `save_dir` contains:

- `checkpoint_ep{N}.pt` – policy weights, agent config, epsilon.
- `metrics.json` – serialized `TrainingConfig`, episode rewards, losses,
  evaluation history, and rollout history.
- `policy_rollouts.jsonl` – optional JSON lines describing deterministic
  rollouts (each entry captures per-step actions/rewards/termination flags).

Metrics include:

- Episode rewards/losses (stored in `trainer.episode_rewards/episode_losses`).
- Evaluation summaries (mean reward, win rate, average length).
- Rollout snapshots when enabled.

## Usage Patterns

- **Resume training** by loading the latest checkpoint prior to instantiating
  `Trainer` and reusing `metrics.json` for context.
- **Self-play**: pass `--opponent self` to mirror the learning agent.
- **Baseline comparison**: use `--opponent PATH` with a frozen checkpoint to
  gauge improvements.
- **Policy rollouts**: enable via `--rollout-episodes N` to record deterministic
  episodes that can feed UI replays or debug notebooks.
