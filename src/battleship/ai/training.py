"""Training loop for the Battleship DQN agent."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from battleship.ai.agent import AgentConfig, DQNAgent
from battleship.ai.environment import BattleshipEnv


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


class Trainer:
    """Coordinates env-agent interaction and logging."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
        self.save_path = Path(config.save_dir)
        self.save_path.mkdir(parents=True, exist_ok=True)

        self.env = BattleshipEnv(rng_seed=config.env_seed)

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

    def _train_episode(self, episode_index: int) -> dict[str, float]:
        obs, info = self.env.reset()
        total_reward = 0.0
        losses: list[float] = []

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
        metrics = {
            "reward": total_reward,
            "steps": float(step + 1),
            "mean_loss": mean_loss,
            "epsilon": self.agent.epsilon,
        }
        self.episode_rewards.append(total_reward)
        self.episode_losses.append(mean_loss)
        return metrics

    def _evaluate(self) -> dict[str, float]:
        rewards = []
        wins = 0
        lengths = []
        cached_epsilon = self.agent.epsilon
        self.agent.epsilon = 0.0

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
        metrics = {
            "mean_reward": float(np.mean(rewards)) if rewards else 0.0,
            "win_rate": wins / max(1, self.config.eval_episodes),
            "avg_length": float(np.mean(lengths) if lengths else 0.0),
        }
        self.eval_history.append(metrics)
        return metrics

    def _save_metrics(self) -> None:
        payload = {
            "config": asdict(self.config),
            "episode_rewards": self.episode_rewards,
            "episode_losses": self.episode_losses,
            "eval_history": self.eval_history,
        }
        (self.save_path / "metrics.json").write_text(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Battleship DQN agent")
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--save-dir", type=str, default="training_artifacts")
    args = parser.parse_args()

    config = TrainingConfig(num_episodes=args.episodes, save_dir=args.save_dir)
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


if __name__ == "__main__":
    main()
