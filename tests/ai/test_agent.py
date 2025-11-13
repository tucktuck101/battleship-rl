"""Unit tests for the Battleship DQN agent stack."""

from __future__ import annotations

import random
from pathlib import Path
from typing import TypeAlias

import numpy as np
import numpy.typing as npt
import pytest
import torch
from battleship.ai.agent import AgentConfig, BattleshipDQN, DQNAgent, ReplayBuffer

C = 6
NUM_ACTIONS = 100
NDArrayFloat: TypeAlias = npt.NDArray[np.float32]


def test_network_forward_shapes() -> None:
    model = BattleshipDQN(in_channels=C, num_actions=NUM_ACTIONS)
    batch = torch.randn(4, C, 10, 10)
    output = model(batch)
    assert "q_values" in output
    assert output["q_values"].shape == (4, NUM_ACTIONS)


def test_replay_buffer_push_and_sample() -> None:
    device = torch.device("cpu")
    buffer = ReplayBuffer(capacity=10, state_shape=(C, 10, 10), device=device)

    dummy_state = np.zeros((C, 10, 10), dtype=np.float32)
    for i in range(8):
        buffer.push(dummy_state, i % NUM_ACTIONS, float(i), dummy_state, False)

    assert len(buffer) == 8
    states, actions, rewards, next_states, dones = buffer.sample(batch_size=4)
    assert states.shape == (4, C, 10, 10)
    assert actions.shape == (4,)
    assert rewards.shape == (4,)
    assert next_states.shape == (4, C, 10, 10)
    assert dones.shape == (4,)


def test_select_action_epsilon_greedy(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AgentConfig(
        epsilon_start=1.0,
        epsilon_end=0.0,
        epsilon_decay=1.0,
        buffer_capacity=10,
        min_buffer_size=1,
        batch_size=1,
    )
    agent = DQNAgent(obs_channels=C, num_actions=NUM_ACTIONS, config=config)

    # Monkeypatch policy network to return deterministic q-values
    q_values = torch.linspace(0, 1, NUM_ACTIONS, device=agent.device).unsqueeze(0)

    def fake_forward(x: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"q_values": q_values.repeat(x.size(0), 1)}

    monkeypatch.setattr(agent.policy_net, "forward", fake_forward)

    obs = np.zeros((C, 10, 10), dtype=np.float32)
    legal_actions = [10, 20, 30]

    random_actions = {agent.select_action(obs, legal_actions, training=True) for _ in range(20)}
    assert random_actions.issubset(set(legal_actions))

    agent.epsilon = 0.0
    greedy_action = agent.select_action(obs, legal_actions, training=True)
    assert greedy_action == max(legal_actions, key=lambda a: q_values[0, a].item())


def test_save_and_load_agent(tmp_path: Path) -> None:
    config = AgentConfig(buffer_capacity=10, min_buffer_size=1, batch_size=1)
    agent = DQNAgent(obs_channels=C, num_actions=NUM_ACTIONS, config=config)

    for param in agent.policy_net.parameters():
        param.data.uniform_(-0.1, 0.1)

    checkpoint = tmp_path / "agent.pt"
    agent.save(checkpoint)

    new_agent = DQNAgent(obs_channels=C, num_actions=NUM_ACTIONS, config=config)
    new_agent.load(checkpoint)

    for p_old, p_new in zip(
        agent.policy_net.state_dict().values(), new_agent.policy_net.state_dict().values()
    ):
        assert torch.allclose(p_old, p_new)


def test_train_step_returns_loss() -> None:
    config = AgentConfig(
        buffer_capacity=200,
        min_buffer_size=32,
        batch_size=32,
        target_update_interval=10,
    )
    agent = DQNAgent(
        obs_channels=C, num_actions=NUM_ACTIONS, config=config, device=torch.device("cpu")
    )

    def random_state() -> NDArrayFloat:
        return np.random.rand(C, 10, 10).astype(np.float32)

    for _ in range(config.min_buffer_size):
        state = random_state()
        next_state = random_state()
        action = random.randint(0, NUM_ACTIONS - 1)
        reward = random.random()
        done = random.random() < 0.1
        agent.store_transition(state, action, reward, next_state, done)

    loss = agent.train_step()
    assert isinstance(loss, float)
