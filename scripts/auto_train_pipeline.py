#!/usr/bin/env python3
"""
Adaptive multi-phase training pipeline for Battleship RL.

Run from repo root:

    PYTHONPATH=src python3 scripts/auto_train_pipeline.py

Phases:
  1. random_baseline     – train vs random opponent (curriculum start)
  2. vs_baseline_ckpt    – train vs frozen baseline checkpoint
  3. self_play           – optional self-play phase (same agent on both sides)

Each phase:
  - Trains in "epochs" of episodes.
  - Evaluates at the end of each epoch.
  - Uses win-rate based criteria to decide when to advance.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from opentelemetry.instrumentation.logging import LoggingInstrumentor

from battleship.ai.training import Trainer, TrainingConfig
from battleship.telemetry import TelemetryConfig, get_tracer, init_telemetry

# ---------------------------------------------------------------------------
# High-level configuration
# ---------------------------------------------------------------------------


RUNS_DIR = Path("runs")
logger = logging.getLogger(__name__)
_TRACER_NAME = "battleship.pipeline.auto"


@dataclass
class EpochCriteria:
    """Controls when a phase should stop and hand off to the next phase."""

    episodes_per_epoch: int
    max_epochs: int
    min_epochs: int
    target_win_rate: float
    patience: int  # number of consecutive good epochs required


# Reasonable defaults; adjust to taste / machine budget.
RANDOM_PHASE_CRITERIA = EpochCriteria(
    episodes_per_epoch=100,
    max_epochs=30,
    min_epochs=5,
    target_win_rate=0.80,  # 80%+ vs random
    patience=3,
)

VS_BASELINE_CRITERIA = EpochCriteria(
    episodes_per_epoch=100,
    max_epochs=30,
    min_epochs=5,
    target_win_rate=0.65,  # a bit lower threshold vs a stronger opponent
    patience=3,
)

SELF_PLAY_CRITERIA = EpochCriteria(
    episodes_per_epoch=100,
    max_epochs=40,
    min_epochs=8,
    target_win_rate=0.55,  # self-play can be more volatile
    patience=4,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ready_to_advance(
    history: list[dict[str, float]],
    criteria: EpochCriteria,
) -> bool:
    """
    Decide if a phase is "good enough" to stop, based on recent win rates.

    Conditions:
      - Have trained for at least min_epochs.
      - The last `criteria.patience` epochs all have win_rate >= target_win_rate.
    """
    if len(history) < criteria.min_epochs:
        return False
    if len(history) < criteria.patience:
        return False

    recent = history[-criteria.patience :]
    return all(ep["win_rate"] >= criteria.target_win_rate for ep in recent)


def run_phase_adaptive(
    phase_name: str,
    base_config: TrainingConfig,
    criteria: EpochCriteria,
) -> Path:
    """
    Run one training phase with adaptive epoch-based stopping.

    Returns:
        Path to the last checkpoint saved for this phase.
    """
    save_dir = Path(base_config.save_dir)
    ensure_dir(save_dir)

    # Optionally set num_episodes to an upper bound for logging purposes only.
    max_total_episodes = criteria.episodes_per_epoch * criteria.max_epochs
    config = replace(base_config, num_episodes=max_total_episodes)

    logger.info(
        "phase_start",
        extra={
            "phase": phase_name,
            "save_dir": str(save_dir),
            "opponent": config.opponent,
            "opponent_checkpoint": config.opponent_checkpoint,
            "episodes_per_epoch": criteria.episodes_per_epoch,
            "max_epochs": criteria.max_epochs,
            "min_epochs": criteria.min_epochs,
            "target_win_rate": criteria.target_win_rate,
            "patience": criteria.patience,
        },
    )

    trainer = Trainer(config)

    epoch_metrics_history: list[dict[str, float]] = []
    total_episodes_run = 0
    last_checkpoint: Optional[Path] = None

    phase_tracer = get_tracer(_TRACER_NAME)

    with phase_tracer.start_as_current_span(
        "pipeline.phase", attributes={"phase": phase_name}
    ):
        for epoch_idx in range(1, criteria.max_epochs + 1):
            # ----------------- training episodes for this epoch -----------------
            for _ in range(criteria.episodes_per_epoch):
                total_episodes_run += 1
                metrics = trainer._train_episode(episode_index=total_episodes_run)
                logger.info(
                    "phase_episode",
                    extra={
                        "phase": phase_name,
                        "episode": total_episodes_run,
                        "reward": metrics["reward"],
                        "steps": metrics["steps"],
                        "mean_loss": metrics["mean_loss"],
                        "epsilon": metrics["epsilon"],
                    },
                )

            # ----------------- evaluation at end of epoch -----------------------
            eval_metrics = trainer._evaluate()
            epoch_metrics_history.append(eval_metrics)
            logger.info(
                "phase_epoch_eval",
                extra={
                    "phase": phase_name,
                    "epoch": epoch_idx,
                    "mean_reward": eval_metrics["mean_reward"],
                    "win_rate": eval_metrics["win_rate"],
                    "avg_length": eval_metrics["avg_length"],
                },
            )

        # Save checkpoint and metrics after each epoch
        checkpoint = save_dir / f"checkpoint_epoch{epoch_idx}.pt"
        trainer.agent.save(checkpoint)
        trainer._save_metrics()
        last_checkpoint = checkpoint

        # Decide whether to stop this phase
        if ready_to_advance(epoch_metrics_history, criteria):
            logger.info(
                "phase_criteria_met",
                extra={"phase": phase_name, "epoch": epoch_idx},
            )
            break

    if last_checkpoint is None:
        # Should never happen if max_epochs >= 1, but keep a defensive path.
        last_checkpoint = save_dir / "checkpoint_final.pt"
        trainer.agent.save(last_checkpoint)
        trainer._save_metrics()
        logger.warning(
            "phase_no_checkpoint",
            extra={"phase": phase_name, "fallback": str(last_checkpoint)},
        )
    logger.info(
        "phase_complete",
        extra={
            "phase": phase_name,
            "epochs": len(epoch_metrics_history),
            "episodes": total_episodes_run,
            "last_checkpoint": str(last_checkpoint),
        },
    )
    return last_checkpoint


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def main() -> None:
    _configure_pipeline_telemetry()
    logger.info("pipeline_start")
    ensure_dir(RUNS_DIR)

    # ----------------- Phase 1: vs random opponent -------------------------
    random_cfg = TrainingConfig(
        save_dir=str(RUNS_DIR / "random_baseline"),
        opponent="random",
        opponent_checkpoint=None,
        opponent_manual_placement=False,
        # other hyperparameters use TrainingConfig defaults
    )
    baseline_ckpt = run_phase_adaptive(
        phase_name="random_baseline",
        base_config=random_cfg,
        criteria=RANDOM_PHASE_CRITERIA,
    )

    # ----------------- Phase 2: vs frozen baseline checkpoint --------------
    vs_baseline_cfg = TrainingConfig(
        save_dir=str(RUNS_DIR / "vs_baseline_ckpt"),
        opponent="checkpoint",
        opponent_checkpoint=str(baseline_ckpt),
        opponent_manual_placement=False,
    )
    vs_baseline_ckpt = run_phase_adaptive(
        phase_name="vs_baseline_ckpt",
        base_config=vs_baseline_cfg,
        criteria=VS_BASELINE_CRITERIA,
    )

    # ----------------- Phase 3: self-play (optional) -----------------------
    self_play_cfg = TrainingConfig(
        save_dir=str(RUNS_DIR / "self_play"),
        opponent="self",
        opponent_checkpoint=None,
        opponent_manual_placement=False,
    )
    self_play_ckpt = run_phase_adaptive(
        phase_name="self_play",
        base_config=self_play_cfg,
        criteria=SELF_PLAY_CRITERIA,
    )

    logger.info(
        "pipeline_complete",
        extra={
            "random_baseline": str(baseline_ckpt),
            "vs_baseline_ckpt": str(vs_baseline_ckpt),
            "self_play": str(self_play_ckpt),
        },
    )


if __name__ == "__main__":
    main()


_TELEMETRY_CONFIGURED = False


def _configure_pipeline_telemetry() -> None:
    global _TELEMETRY_CONFIGURED
    if _TELEMETRY_CONFIGURED:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    normalized = _normalize_endpoint(endpoint)
    config = TelemetryConfig(
        enable_tracing=True,
        enable_metrics=True,
        enable_logging=True,
        otlp_traces_endpoint=normalized,
        otlp_metrics_endpoint=normalized,
        otlp_logs_endpoint=normalized,
        service_name="battleship-pipeline",
        service_namespace="ml",
    )
    init_telemetry(config)
    LoggingInstrumentor().instrument()
    _TELEMETRY_CONFIGURED = True


def _normalize_endpoint(value: str | None) -> str | None:
    if not value:
        return None
    return value.removeprefix("http://").removeprefix("https://")
