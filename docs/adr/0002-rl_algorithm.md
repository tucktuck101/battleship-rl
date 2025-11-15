# ADR 0002 – Dueling DQN for Battleship AI

- **Status**: Accepted
- **Date**: 2024-01-01
- **Context**: RL Agent & Trainer

## Context

The Battleship RL stack requires a policy that:

1. Operates on grid-like observations (multi-channel 10×10 inputs).
2. Supports action masking for illegal moves (shots already taken, placement conflicts).
3. Trains efficiently on CPUs/GPUs available to contributors.
4. Provides stable exploration with repeatable results.

We considered policy-gradient families (PPO/A2C), tabular Q-learning, and
convolutional DQNs. Battleship’s discrete board and action mask suit value-based
methods without continuous control overhead.

## Decision

- **Algorithm**: Dueling Deep Q-Network (DQN).
  - Backbone: 3-layer CNN (32/64/64 channels) with 10×10 inputs.
  - Heads: value stream + advantage stream aggregated into Q-values.
- **Exploration**: Epsilon-greedy with configurable schedule. Default: start 1.0,
  decay 0.995 per train step until 0.05.
- **Replay Buffer**: Fixed-size circular buffer, 100k capacity, sampling 64-sized
  minibatches once the buffer holds at least 1k transitions.
- **Target Network**: Hard update every 1,000 optimizer steps to stabilize Q-targets.
- **Reward Shaping**: Based on `BattleshipEnv` constants (hit reward, miss penalty,
  invalid action penalty, win/loss bonuses).
- **Opponent Modes**: Random baseline, self-play, or loaded checkpoint for curriculum.

## Consequences

- CNN-friendly observations allow GPU acceleration without exotic architecture
  engineering.
- Value-based policies need deterministic environments—already satisfied by
  `BattleshipEnv`.
- Replay buffers + epsilon schedules require additional configuration; surfaced
  via `TrainingConfig` and documented in `docs/training_config.md`.
- Extending to other algorithms (PPO, self-supervised) requires new ADRs and
  adjustments to telemetry + training CLI.
