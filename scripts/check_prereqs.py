#!/usr/bin/env python3
"""
Prerequisite checker for battleship-rl (no CUDA checks).

Run from repo root (after activating your venv):

    python3 scripts/check_prereqs.py
"""

import sys
import traceback
from pathlib import Path


def add_src_to_syspath() -> None:
    """Ensure `src/` is on sys.path so `import battleship` works."""
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def check_python_version() -> bool:
    header("1) Python version")
    v = sys.version_info
    print(f"Detected Python: {v.major}.{v.minor}.{v.micro}")
    ok = (v.major == 3 and v.minor >= 10) or (v.major > 3)
    if ok:
        print("OK: Python 3.10 or newer is available.")
    else:
        print("FAIL: Python 3.10+ required for this project.")
    return ok


def check_core_imports() -> bool:
    header("2) Core library imports (gymnasium, torch, pygame, numpy)")
    libs = ["gymnasium", "torch", "pygame", "numpy"]
    all_ok = True
    for name in libs:
        try:
            __import__(name)
            print(f"OK: imported {name}")
        except Exception as exc:  # noqa: BLE001
            all_ok = False
            print(f"FAIL: could not import {name}: {exc}")
            traceback.print_exc(limit=1)
    return all_ok


def check_battleship_imports() -> bool:
    header("3) Battleship engine / AI imports")
    add_src_to_syspath()
    ok = True
    try:
        from battleship.ai.environment import BattleshipEnv  # noqa: F401
        from battleship.ai.training import Trainer, TrainingConfig  # noqa: F401
        from battleship.engine.game import BattleshipGame  # noqa: F401

        print("OK: imported BattleshipGame, BattleshipEnv, TrainingConfig, Trainer")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"FAIL: could not import battleship modules: {exc}")
        traceback.print_exc(limit=1)
    return ok


def check_env_smoke_test() -> bool:
    header("4) Environment smoke test (reset(), observation, action_mask)")
    add_src_to_syspath()
    try:
        from battleship.ai.environment import BattleshipEnv

        env = BattleshipEnv()
        obs, info = env.reset()
        print("OK: env.reset() succeeded.")
        print(f"    Observation shape: {obs.shape}")
        mask = info.get("action_mask")
        if mask is None:
            print("FAIL: info did not contain 'action_mask'")
            return False
        print(f"    Action mask length: {len(mask)} (non-zero entries: {mask.sum()})")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: environment smoke test failed: {exc}")
        traceback.print_exc(limit=1)
        return False


def check_trainer_smoke_test() -> bool:
    header("5) Trainer + DQN smoke test (1 short episode)")
    add_src_to_syspath()
    try:
        from battleship.ai.training import Trainer, TrainingConfig

        cfg = TrainingConfig(num_episodes=1, max_steps_per_episode=50)
        trainer = Trainer(cfg)
        print("OK: Trainer initialised.")

        metrics = trainer._train_episode(episode_index=0)
        print("OK: one training episode completed.")
        print(
            f"    reward={metrics['reward']:.2f}, "
            f"steps={metrics['steps']:.0f}, "
            f"mean_loss={metrics['mean_loss']:.4f}, "
            f"epsilon={metrics['epsilon']:.3f}"
        )
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: trainer smoke test failed: {exc}")
        traceback.print_exc(limit=1)
        return False


def main() -> None:
    checks = [
        ("Python version", check_python_version),
        ("Core imports", check_core_imports),
        ("Battleship imports", check_battleship_imports),
        ("Environment smoke test", check_env_smoke_test),
        ("Trainer smoke test", check_trainer_smoke_test),
    ]

    overall_ok = True
    results: list[tuple[str, bool]] = []

    for name, fn in checks:
        ok = fn()
        results.append((name, ok))
        overall_ok = overall_ok and ok

    header("Summary")
    for name, ok in results:
        status = "OK  " if ok else "FAIL"
        print(f"{status} - {name}")

    print("\n" + "=" * 72)
    if overall_ok:
        print("ALL CHECKS PASSED: you are ready to train your Battleship agent.")
        print("Next step example:")
        print("    PYTHONPATH=src python3 -m battleship.ai.training --episodes 10")
    else:
        print("Some checks FAILED. Review the messages above and fix them before training.")
    print("=" * 72)


if __name__ == "__main__":
    main()
