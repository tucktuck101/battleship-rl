"""Training loop for the Battleship DQN agent."""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from battleship.ai.agent import AgentConfig, DQNAgent
from battleship.ai.environment import BattleshipEnv
from battleship.telemetry import (
    TelemetryConfig,
    get_meter,
    get_tracer,
    init_telemetry,
)

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    num_episodes: int = 200
    max_steps_per_episode: int = 500
    eval_interval: int = 20
    eval_episodes: int = 5
    gamma: float = 0.99
    lr: float = 1e-3
    batch_size: int = 64
    buffer_capacity: int = 100_000
    min_buffer_size: int = 1_000
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995
    target_update_interval: int = 1_000
    env_seed: int | None = 42
    agent_seed: int | None = 7
    save_dir: str = "training_artifacts"
    opponent: str = "random"
    opponent_checkpoint: str | None = None
    opponent_manual_placement: bool = False
    rollout_episodes: int = 0
    rollout_path: str = "policy_rollouts.jsonl"


class Trainer:
    """Coordinates env-agent interaction and logging."""

    def __init__(self, config: TrainingConfig, opponent_agent: DQNAgent | None = None) -> None:
        self.config = config
        self.save_path = Path(config.save_dir)
        self.save_path.mkdir(parents=True, exist_ok=True)

        self._configure_telemetry()
        self.tracer = get_tracer()
        self.meter = get_meter()
        self.episode_reward_hist = self.meter.create_histogram(
            "battleship_episode_reward",
            unit="1",
            description="Total reward per training episode",
        )
        self.episode_loss_hist = self.meter.create_histogram(
            "battleship_episode_mean_loss",
            unit="1",
            description="Mean loss per training episode",
        )
        self.eval_win_rate_hist = self.meter.create_histogram(
            "battleship_eval_win_rate",
            unit="1",
            description="Win rate observed during evaluation",
        )
        logger.info(
            "trainer_initialised",
            extra={
                "episodes": config.num_episodes,
                "save_dir": config.save_dir,
                "opponent": config.opponent,
            },
        )

        self.env = BattleshipEnv(
            rng_seed=config.env_seed,
            allow_opponent_placement=config.opponent_manual_placement,
        )
        self.opponent_agent: DQNAgent | None = opponent_agent

        agent_config = AgentConfig(
            gamma=config.gamma,
            lr=config.lr,
            batch_size=config.batch_size,
            buffer_capacity=config.buffer_capacity,
            min_buffer_size=config.min_buffer_size,
            epsilon_start=config.epsilon_start,
            epsilon_end=config.epsilon_end,
            epsilon_decay=config.epsilon_decay,
            target_update_interval=config.target_update_interval,
        )

        if config.agent_seed is not None:
            np.random.seed(config.agent_seed)

        obs_channels = self.env.observation_space.shape[0]
        self.agent = DQNAgent(obs_channels=obs_channels, config=agent_config)

        self.episode_rewards: list[float] = []
        self.episode_losses: list[float] = []
        self.eval_history: list[dict[str, float]] = []
        self.rollout_history: list[dict[str, Any]] = []
        self._initialise_opponent_agent(obs_channels=obs_channels, agent_config=agent_config)

    def _configure_telemetry(self) -> None:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        normalized = self._normalize_endpoint(endpoint)
        config = TelemetryConfig(
            enable_tracing=True,
            enable_metrics=True,
            enable_logging=True,
            otlp_traces_endpoint=normalized,
            otlp_metrics_endpoint=normalized,
            otlp_logs_endpoint=normalized,
            service_name="battleship-trainer",
            service_namespace="ml",
        )
        init_telemetry(config)
        LoggingInstrumentor().instrument()

    @staticmethod
    def _normalize_endpoint(value: str | None) -> str | None:
        if not value:
            return None
        return value.removeprefix("http://").removeprefix("https://")

    def _initialise_opponent_agent(self, obs_channels: int, agent_config: AgentConfig) -> None:
        """Attach an opponent agent (self, checkpoint, or external)."""

        if self.opponent_agent is None:
            if self.config.opponent == "self":
                self.opponent_agent = self.agent
            elif self.config.opponent == "checkpoint":
                checkpoint = self.config.opponent_checkpoint
                if checkpoint is None:
                    raise ValueError("opponent checkpoint path must be provided.")
                opponent = DQNAgent(obs_channels=obs_channels, config=agent_config)
                opponent.load(checkpoint)
                opponent.epsilon = 0.0
                self.opponent_agent = opponent

        if self.opponent_agent is not None:
            self.env.opponent_policy = self._opponent_policy_wrapper
            if self.config.opponent_manual_placement:
                self.env.opponent_placement_policy = self._opponent_policy_wrapper

    def _opponent_policy_wrapper(self, obs: np.ndarray, info: dict[str, Any]) -> int:
        if self.opponent_agent is None:
            raise RuntimeError("Opponent agent not initialised.")
        legal_actions = info.get("action_mask")
        return self.opponent_agent.select_action(obs, legal_actions, training=False)

    def _train_episode(self, episode_index: int) -> dict[str, float]:
        with self.tracer.start_as_current_span("train_episode") as span:
            obs, info = self.env.reset()
            total_reward = 0.0
            losses: list[float] = []

            step = -1
            for step in range(self.config.max_steps_per_episode):
                legal_actions = info.get("action_mask")
                action = self.agent.select_action(obs, legal_actions=legal_actions, training=True)
                next_obs, reward, terminated, truncated, info = self.env.step(action)
                done = terminated or truncated

                self.agent.store_transition(obs, action, reward, next_obs, done)
                loss = self.agent.train_step()
                if loss is not None:
                    losses.append(loss)
                self.agent.decay_epsilon()

                total_reward += reward
                obs = next_obs
                if done:
                    break

            mean_loss = float(np.mean(losses)) if losses else 0.0
            step_count = step + 1 if step >= 0 else 0
            metrics = {
                "reward": total_reward,
                "steps": float(step_count),
                "mean_loss": mean_loss,
                "epsilon": self.agent.epsilon,
            }
            span.set_attribute("episode.index", episode_index)
            span.set_attribute("episode.reward", total_reward)
            span.set_attribute("episode.steps", step_count)
            span.set_attribute("agent.epsilon", self.agent.epsilon)

            self.episode_reward_hist.record(total_reward)
            self.episode_loss_hist.record(mean_loss)

            self.episode_rewards.append(total_reward)
            self.episode_losses.append(mean_loss)

            logger.info(
                "train_episode",
                extra={
                    "episode_index": episode_index,
                    "reward": total_reward,
                    "steps": step_count,
                    "mean_loss": mean_loss,
                    "epsilon": self.agent.epsilon,
                },
            )
            return metrics

    def _evaluate(self) -> dict[str, float]:
        with self.tracer.start_as_current_span("evaluate_agent") as span:
            rewards = []
            wins = 0
            lengths = []
            cached_epsilon = self.agent.epsilon
            self.agent.epsilon = 0.0
            opponent_cached: float | None = None
            if self.opponent_agent is not None and self.opponent_agent is not self.agent:
                opponent_cached = getattr(self.opponent_agent, "epsilon", None)
                if opponent_cached is not None:
                    self.opponent_agent.epsilon = 0.0

            for _ in range(self.config.eval_episodes):
                obs, info = self.env.reset()
                episode_reward = 0.0
                for step in range(self.config.max_steps_per_episode):
                    action = self.agent.select_action(obs, info.get("action_mask"), training=False)
                    obs, reward, terminated, truncated, info = self.env.step(action)
                    episode_reward += reward
                    if terminated or truncated:
                        if info.get("winner") == "PLAYER1":
                            wins += 1
                        lengths.append(step + 1)
                        break
                rewards.append(episode_reward)

            self.agent.epsilon = cached_epsilon
            if (
                self.opponent_agent is not None
                and self.opponent_agent is not self.agent
                and opponent_cached is not None
            ):
                self.opponent_agent.epsilon = opponent_cached
            metrics = {
                "mean_reward": float(np.mean(rewards)) if rewards else 0.0,
                "win_rate": wins / max(1, self.config.eval_episodes),
                "avg_length": float(np.mean(lengths) if lengths else 0.0),
            }
            span.set_attribute("eval.mean_reward", metrics["mean_reward"])
            span.set_attribute("eval.win_rate", metrics["win_rate"])
            span.set_attribute("eval.avg_length", metrics["avg_length"])
            self.eval_win_rate_hist.record(metrics["win_rate"])

            logger.info(
                "evaluate_agent",
                extra={
                    "mean_reward": metrics["mean_reward"],
                    "win_rate": metrics["win_rate"],
                    "avg_length": metrics["avg_length"],
                },
            )

            self.eval_history.append(metrics)
            return metrics

    def _policy_rollout(
        self, episodes: int | None = None, output_path: Path | None = None
    ) -> list[dict[str, Any]]:
        """Generate rollout summaries for deterministic policy playthroughs."""

        total_episodes = episodes if episodes is not None else self.config.rollout_episodes
        if total_episodes <= 0:
            return []

        results: list[dict[str, Any]] = []
        cached_epsilon = self.agent.epsilon
        self.agent.epsilon = 0.0
        opponent_cached: float | None = None
        if self.opponent_agent is not None and self.opponent_agent is not self.agent:
            opponent_cached = getattr(self.opponent_agent, "epsilon", None)
            if opponent_cached is not None:
                self.opponent_agent.epsilon = 0.0

        for episode in range(1, total_episodes + 1):
            obs, info = self.env.reset()
            trajectory: list[dict[str, Any]] = []
            total_reward = 0.0
            steps = 0
            terminated_flag = False
            truncated_flag = False

            for _ in range(self.config.max_steps_per_episode):
                mask = info.get("action_mask")
                action = self.agent.select_action(obs, mask, training=False)
                obs, reward, terminated, truncated, info = self.env.step(action)
                trajectory.append(
                    {
                        "step": steps,
                        "action": action,
                        "reward": reward,
                        "phase": info.get("phase"),
                    }
                )
                total_reward += reward
                steps += 1
                terminated_flag = terminated
                truncated_flag = truncated
                if terminated_flag or truncated_flag:
                    break

            summary = {
                "episode": episode,
                "steps": steps,
                "total_reward": total_reward,
                "winner": info.get("winner"),
                "terminated": terminated_flag,
                "truncated": truncated_flag,
                "trajectory": trajectory,
            }
            results.append(summary)

        self.agent.epsilon = cached_epsilon
        if (
            self.opponent_agent is not None
            and self.opponent_agent is not self.agent
            and opponent_cached is not None
        ):
            self.opponent_agent.epsilon = opponent_cached

        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("a", encoding="utf-8") as fp:
                for summary in results:
                    fp.write(json.dumps(summary) + "\n")

        self.rollout_history.extend(results)
        return results

    def _save_metrics(self) -> None:
        payload = {
            "config": asdict(self.config),
            "episode_rewards": self.episode_rewards,
            "episode_losses": self.episode_losses,
            "eval_history": self.eval_history,
            "rollout_history": self.rollout_history,
        }
        (self.save_path / "metrics.json").write_text(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Battleship DQN agent")
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--save-dir", type=str, default="training_artifacts")
    parser.add_argument(
        "--opponent",
        type=str,
        default="random",
        help=("Opponent type: 'random' (default), 'self', or the path to a checkpoint."),
    )
    parser.add_argument(
        "--opponent-placement",
        action="store_true",
        help="Let the opponent place its own ships via its policy.",
    )
    parser.add_argument(
        "--rollout-episodes",
        type=int,
        default=0,
        help="Number of policy rollout episodes to record after each evaluation interval.",
    )
    parser.add_argument(
        "--rollout-path",
        type=str,
        default="policy_rollouts.jsonl",
        help="Relative path (under save-dir) for JSONL rollout summaries.",
    )
    args = parser.parse_args()

    opponent_mode = "random"
    opponent_checkpoint: str | None = None
    if args.opponent == "self":
        opponent_mode = "self"
    elif args.opponent != "random":
        opponent_mode = "checkpoint"
        opponent_checkpoint = args.opponent

    config = TrainingConfig(
        num_episodes=args.episodes,
        save_dir=args.save_dir,
        opponent=opponent_mode,
        opponent_checkpoint=opponent_checkpoint,
        opponent_manual_placement=args.opponent_placement,
        rollout_episodes=args.rollout_episodes,
        rollout_path=args.rollout_path,
    )
    trainer = Trainer(config)

    for episode in range(1, config.num_episodes + 1):
        metrics = trainer._train_episode(episode)
        print(
            f"[Episode {episode}/{config.num_episodes}] "
            f"reward={metrics['reward']:.2f} steps={metrics['steps']:.0f} "
            f"loss={metrics['mean_loss']:.4f} epsilon={metrics['epsilon']:.3f}"
        )

        if episode % config.eval_interval == 0:
            eval_metrics = trainer._evaluate()
            print(
                f"  Eval -> mean_reward={eval_metrics['mean_reward']:.2f} "
                f"win_rate={eval_metrics['win_rate']:.2%} "
                f"avg_length={eval_metrics['avg_length']:.1f}"
            )
            checkpoint = Path(config.save_dir) / f"checkpoint_ep{episode}.pt"
            trainer.agent.save(checkpoint)
            trainer._save_metrics()
            if config.rollout_episodes > 0:
                rollout_file = Path(config.save_dir) / config.rollout_path
                rollouts = trainer._policy_rollout(output_path=rollout_file)
                display_path = (
                    rollout_file.relative_to(Path.cwd())
                    if rollout_file.is_absolute()
                    else rollout_file
                )
                print(f"  Rollout -> recorded {len(rollouts)} episodes to {display_path}")


if __name__ == "__main__":
    main()
