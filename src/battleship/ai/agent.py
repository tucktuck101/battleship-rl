"""PyTorch DQN agent for the Battleship environment."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence, TypeAlias

import numpy as np
import numpy.typing as npt
import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812


class BattleshipDQN(nn.Module):
    """Dueling DQN architecture for Battleship observations."""

    def __init__(self, in_channels: int, hidden_dim: int = 256, num_actions: int = 100):
        super().__init__()
        self.num_actions = num_actions

        self.backbone = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
        )

        backbone_dim = 64 * 10 * 10

        self.value_head = nn.Sequential(
            nn.Linear(backbone_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, 1),
        )

        self.adv_head = nn.Sequential(
            nn.Linear(backbone_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, num_actions),
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.backbone(x)
        flat = features.view(features.size(0), -1)
        value = self.value_head(flat)
        advantage = self.adv_head(flat)
        advantage_mean = advantage.mean(dim=1, keepdim=True)
        q_values = value + advantage - advantage_mean
        return {"q_values": q_values, "value": value, "advantage": advantage}


NDArrayFloat: TypeAlias = npt.NDArray[np.float32]
MaskArray: TypeAlias = npt.NDArray[np.float64]
TensorLike: TypeAlias = torch.Tensor | NDArrayFloat


class ReplayBuffer:
    """Fixed-size replay memory storing transition tuples."""

    def __init__(self, capacity: int, state_shape: Sequence[int], device: torch.device):
        self.capacity = capacity
        self.device = device
        self.state_shape = tuple(state_shape)

        self.states = torch.zeros((capacity, *self.state_shape), dtype=torch.float32, device=device)
        self.next_states = torch.zeros_like(self.states)
        self.actions = torch.zeros(capacity, dtype=torch.long, device=device)
        self.rewards = torch.zeros(capacity, dtype=torch.float32, device=device)
        self.dones = torch.zeros(capacity, dtype=torch.float32, device=device)

        self.position = 0
        self.size = 0

    def __len__(self) -> int:
        return self.size

    def push(
        self,
        state: TensorLike,
        action: int,
        reward: float,
        next_state: TensorLike,
        done: bool,
    ) -> None:
        idx = self.position
        self.states[idx] = self._to_tensor(state)
        self.next_states[idx] = self._to_tensor(next_state)
        self.actions[idx] = int(action)
        self.rewards[idx] = float(reward)
        self.dones[idx] = float(done)

        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(
        self, batch_size: int
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if self.size == 0:
            raise ValueError("Cannot sample from an empty buffer.")
        indices = torch.randint(0, self.size, (batch_size,), device=self.device)
        return (
            self.states[indices],
            self.actions[indices],
            self.rewards[indices],
            self.next_states[indices],
            self.dones[indices],
        )

    def _to_tensor(self, array: TensorLike) -> torch.Tensor:
        tensor = array.detach() if isinstance(array, torch.Tensor) else torch.from_numpy(array)
        return tensor.to(self.device, dtype=torch.float32)


@dataclass
class AgentConfig:
    gamma: float = 0.99
    lr: float = 1e-3
    batch_size: int = 64
    buffer_capacity: int = 100_000
    min_buffer_size: int = 1_000
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995
    target_update_interval: int = 1_000
    max_grad_norm: float = 1.0


class DQNAgent:
    """High-level API for training and acting with a dueling DQN."""

    def __init__(
        self,
        obs_channels: int,
        num_actions: int = 100,
        config: AgentConfig | None = None,
        device: torch.device | None = None,
    ):
        self.config = config or AgentConfig()
        self.num_actions = num_actions
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.policy_net = BattleshipDQN(obs_channels, num_actions=num_actions).to(self.device)
        self.target_net = BattleshipDQN(obs_channels, num_actions=num_actions).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=self.config.lr)
        self.replay_buffer = ReplayBuffer(
            capacity=self.config.buffer_capacity,
            state_shape=(obs_channels, 10, 10),
            device=self.device,
        )

        self.epsilon = self.config.epsilon_start
        self.train_steps = 0

    def select_action(
        self,
        state: TensorLike,
        legal_actions: MaskArray | Sequence[int] | None = None,
        training: bool = True,
    ) -> int:
        state_tensor = self._prepare_state(state)
        legal = self._legal_actions(legal_actions)

        if training and random.random() < self.epsilon:
            return random.choice(legal)

        with torch.no_grad():
            q_values = self.policy_net(state_tensor)["q_values"].squeeze(0)
            masked_q = self._apply_action_mask(q_values, legal)
            action = int(torch.argmax(masked_q).item())
        return action

    def store_transition(
        self,
        state: TensorLike,
        action: int,
        reward: float,
        next_state: TensorLike,
        done: bool,
    ) -> None:
        self.replay_buffer.push(state, action, reward, next_state, done)

    def train_step(self) -> float | None:
        if len(self.replay_buffer) < self.config.min_buffer_size:
            return None

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            self.config.batch_size
        )

        q_values = self.policy_net(states)["q_values"]
        current_q = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_values = self.target_net(next_states)["q_values"]
            max_next_q = next_q_values.max(dim=1).values
            targets = rewards + self.config.gamma * max_next_q * (1.0 - dones)

        loss_tensor: torch.Tensor = F.mse_loss(current_q, targets)

        self.optimizer.zero_grad()
        loss_tensor.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), self.config.max_grad_norm)
        self.optimizer.step()

        self.train_steps += 1
        if self.train_steps % self.config.target_update_interval == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        return float(loss_tensor.item())

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.config.epsilon_end, self.epsilon * self.config.epsilon_decay)

    def save(self, path: str | Path) -> None:
        payload = {
            "model_state": self.policy_net.state_dict(),
            "config": asdict(self.config),
            "epsilon": self.epsilon,
        }
        torch.save(payload, Path(path))

    def load(self, path: str | Path) -> None:
        payload = torch.load(Path(path), map_location=self.device)
        self.policy_net.load_state_dict(payload["model_state"])
        self.target_net.load_state_dict(payload["model_state"])
        if "config" in payload:
            self.config = AgentConfig(**payload["config"])
        if "epsilon" in payload:
            self.epsilon = float(payload["epsilon"])

    def _prepare_state(self, state: TensorLike) -> torch.Tensor:
        tensor = state.detach() if isinstance(state, torch.Tensor) else torch.from_numpy(state)
        if tensor.ndim == 3:
            tensor = tensor.unsqueeze(0)
        return tensor.to(self.device, dtype=torch.float32)

    def _legal_actions(self, legal_actions: MaskArray | Sequence[int] | None) -> list[int]:
        if legal_actions is None:
            return list(range(self.num_actions))
        if isinstance(legal_actions, np.ndarray):
            if legal_actions.ndim == 1 and legal_actions.shape[0] == self.num_actions:
                return [int(idx) for idx, allowed in enumerate(legal_actions) if allowed]
            return [int(action) for action in legal_actions.tolist()]
        return [int(action) for action in legal_actions]

    def _apply_action_mask(self, q_values: torch.Tensor, legal_actions: list[int]) -> torch.Tensor:
        mask = torch.full_like(q_values, -1e9)
        mask[legal_actions] = 0.0
        return q_values + mask
