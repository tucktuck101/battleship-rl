.PHONY: lint typecheck test test-engine test-env rl-test telemetry-test train check help

PYTHON ?= python3
SRC_DIRS := src tests

help:
	@echo "Available targets:"
	@echo "  make lint          Run ruff and black checks"
	@echo "  make typecheck     Run mypy"
	@echo "  make test          Run full pytest suite"
	@echo "  make test-engine   Run engine-specific tests"
	@echo "  make test-env      Run Gym environment tests"
	@echo "  make rl-test       Run RL agent/training tests"
	@echo "  make telemetry-test Run telemetry-focused tests"
	@echo "  make train         Launch DQN training with defaults"
	@echo "  make check         Run lint, typecheck, and test"

lint:
	ruff check $(SRC_DIRS)
	black --check $(SRC_DIRS)

typecheck:
	PYTHONPATH=src mypy src

test:
	PYTHONPATH=src pytest

test-engine:
	PYTHONPATH=src pytest tests/engine

test-env:
	PYTHONPATH=src pytest tests/ai/test_environment.py

rl-test:
	PYTHONPATH=src pytest tests/ai/test_agent.py tests/ai/test_training_loop.py

telemetry-test:
	PYTHONPATH=src pytest tests/telemetry/test_instrumentation.py

train:
	PYTHONPATH=src python -m battleship.ai.training --episodes 200 --save-dir training_artifacts

check: lint typecheck test
