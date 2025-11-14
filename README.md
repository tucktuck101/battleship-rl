# Battleship RL Playground

Battleship-rl is a reinforcement-learning sandbox for experimenting with Battleship
strategies. It bundles a deterministic engine, a Gymnasium-compatible environment,
telemetry helpers, and multiple front-ends (CLI + Pygame UI) for both human and AI
play.

---

## Features

- **Engine** – Turn-based `BattleshipGame` with board/ship primitives and an
  instrumented variant that emits OpenTelemetry spans, metrics, and logs.
- **AI Stack** – Dueling-DQN implementation (`DQNAgent`), replay buffer, training
  loop, and optional `InstrumentedDQNAgent`.
- **Environment** – `BattleshipEnv` exposes the engine via the Gymnasium API for
  training or evaluation.
  - *Agent placement mode* (opt-in): pass `allow_agent_placement=True` to
    `BattleshipEnv` to let the agent place its own fleet before firing begins.
    The action space expands to encode `(ship_type, orientation, row, col)` moves
    during placement and reverts to standard shot coordinates once the phase
    switches to firing. Observations gain extra channels that indicate which
    ships remain to be placed plus the current phase so policies can react
    without bespoke wiring. Leave the flag at its default (`False`) to retain the
    classic random-placement baseline.
  - *Pluggable opponents*: specify `opponent_policy` directly or choose
    `--opponent self|<checkpoint>` in the trainer to face deterministic bots,
    pretrained checkpoints, or a second live DQN for self-play.
  - *Opponent placement mode* – pass `allow_opponent_placement=True` (or
    `--opponent-placement` via the trainer CLI) so the adversary places its own
    fleet instead of receiving a random layout.
- **Telemetry** – Shared tracer/meter/logger helpers with OTLP exporters.
- **User Interfaces**
  - `scripts/run_ui.py` launches the Pygame UI.
  - `battleship/cli.py` lets you play from the terminal.

---

## Repository Layout

```
.
├── docs/                    # guides (e.g., training tutorial)
├── scripts/run_ui.py        # convenience launcher (sets PYTHONPATH + runs UI)
├── src/battleship/
│   ├── ai/                  # agent, instrumented agent, training loop, env
│   ├── engine/              # board, ship, game, instrumented game
│   ├── telemetry/           # tracer/meter/logger helpers
│   ├── ui/                  # Pygame UI implementation
│   ├── api/                 # FastAPI scaffold (health endpoint)
│   └── cli.py               # text-mode experience
└── tests/                   # pytest suites covering AI + telemetry
```

The legacy reference implementation is retained under `battleship-rl/` for parity
checks but the `src/` tree now contains the authoritative code.

---

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt  # or install torch, gymnasium, pygame, fastapi, etc.

# run the UI (passes args straight to battleship.ui.game_ui)
python3 scripts/run_ui.py --instrumented

# start a training session (see docs/training_tutorial.md for details)
PYTHONPATH=src python3 -m battleship.ai.training --episodes 400 --save-dir runs/baseline
```

Add `--opponent self` for self-play, point `--opponent` at a saved checkpoint
to spar against a fixed agent, and include `--opponent-placement` to force the
enemy to place its own ships during setup.

Once a checkpoint has been produced you can play against it via:

```bash
scripts/run_ui.py --agent runs/baseline/checkpoint_ep400.pt
```

---

## Telemetry

All major components can emit OpenTelemetry data:

- Engine (`InstrumentedBattleshipGame`)
- Agent (`InstrumentedDQNAgent`)
- UI (`BattleshipUI`)

Configure exporters by calling `battleship.telemetry.init_telemetry(...)`
before starting training or launching the UI. Metrics, logs, and traces can
then be shipped to an OTLP collector (or printed locally).

---

## Testing

Run the existing pytest suites:

```bash
PYTHONPATH=src pytest
```

Add similar tests as new modules land (e.g., API endpoints, replay pipeline).

---

## Next Steps

The long-term goal is a web UI (OTel-demo style) for:

1. Managing training configs/jobs
2. Monitoring telemetry + metrics
3. Browsing and replaying AI-vs-AI matches

See `WEB_UI_README.md` for the current roadmap.
