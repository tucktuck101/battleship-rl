"""AI package exports."""

from .environment import BattleshipEnv

__all__ = ["BattleshipEnv"]

try:  # pragma: no cover - registration side effect
    from gymnasium.envs.registration import register
    from gymnasium.error import Error as GymError

    try:
        register(
            id="BattleshipEnv-v0",
            entry_point="battleship.ai.environment:BattleshipEnv",
            max_episode_steps=400,
        )
    except GymError:
        # Already registered; safe to ignore duplicate registrations.
        pass
except ImportError:  # Gymnasium not available
    pass
