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

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from battleship.ai.training import Trainer, TrainingConfig

# ---------------------------------------------------------------------------
# High-level configuration
# ---------------------------------------------------------------------------


RUNS_DIR = Path("runs")


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

    print("=" * 80)
    print(f"Starting phase: {phase_name}")
    print(f"  Save dir:           {save_dir}")
    print(f"  Opponent mode:      {config.opponent}")
    print(f"  Opponent checkpoint:{config.opponent_checkpoint}")
    print(f"  Episodes/epoch:     {criteria.episodes_per_epoch}")
    print(f"  Max epochs:         {criteria.max_epochs}")
    print(f"  Min epochs:         {criteria.min_epochs}")
    print(f"  Target win_rate:    {criteria.target_win_rate:.0%}")
    print(f"  Patience:           {criteria.patience}")
    print("=" * 80)

    trainer = Trainer(config)

    epoch_metrics_history: list[dict[str, float]] = []
    total_episodes_run = 0
    last_checkpoint: Optional[Path] = None

    for epoch_idx in range(1, criteria.max_epochs + 1):
        # ----------------- training episodes for this epoch -----------------
        for _ in range(criteria.episodes_per_epoch):
            total_episodes_run += 1
            metrics = trainer._train_episode(episode_index=total_episodes_run)
            print(
                f"[{phase_name}] Ep {total_episodes_run:5d} "
                f"reward={metrics['reward']:.3f} "
                f"steps={metrics['steps']:.0f} "
                f"mean_loss={metrics['mean_loss']:.4f} "
                f"epsilon={metrics['epsilon']:.3f}"
            )

        # ----------------- evaluation at end of epoch -----------------------
        eval_metrics = trainer._evaluate()
        epoch_metrics_history.append(eval_metrics)
        print(
            f"[{phase_name}] Epoch {epoch_idx:3d} eval -> "
            f"mean_reward={eval_metrics['mean_reward']:.3f} "
            f"win_rate={eval_metrics['win_rate']:.2%} "
            f"avg_length={eval_metrics['avg_length']:.1f}"
        )

        # Save checkpoint and metrics after each epoch
        checkpoint = save_dir / f"checkpoint_epoch{epoch_idx}.pt"
        trainer.agent.save(checkpoint)
        trainer._save_metrics()
        last_checkpoint = checkpoint

        # Decide whether to stop this phase
        if ready_to_advance(epoch_metrics_history, criteria):
            print(f"[{phase_name}] Criteria met at epoch {epoch_idx}; " f"advancing to next phase.")
            break

    if last_checkpoint is None:
        # Should never happen if max_epochs >= 1, but keep a defensive path.
        last_checkpoint = save_dir / "checkpoint_final.pt"
        trainer.agent.save(last_checkpoint)
        trainer._save_metrics()
        print(
            f"[{phase_name}] No checkpoints created unexpectedly; "
            f"saved fallback checkpoint at {last_checkpoint}"
        )

    print(f"[{phase_name}] Completed after {len(epoch_metrics_history)} epochs.")
    print(f"[{phase_name}] Total episodes run: {total_episodes_run}")
    print(f"[{phase_name}] Last checkpoint: {last_checkpoint}")
    print("=" * 80)
    return last_checkpoint


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def main() -> None:
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

    print("Pipeline complete.")
    print(f"  Phase 1 (random_baseline) checkpoint:   {baseline_ckpt}")
    print(f"  Phase 2 (vs_baseline_ckpt) checkpoint:  {vs_baseline_ckpt}")
    print(f"  Phase 3 (self_play) checkpoint:         {self_play_ckpt}")


if __name__ == "__main__":
    main()
