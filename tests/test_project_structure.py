"""Basic project scaffolding tests."""

import importlib


def test_package_importable() -> None:
    """Verify the top-level package is importable."""
    import battleship  # noqa: F401  (import used to ensure availability)

    assert battleship is not None


def test_submodules_exist() -> None:
    """All primary submodules should be importable placeholders."""
    modules = [
        "battleship.engine",
        "battleship.ai",
        "battleship.ui",
        "battleship.telemetry",
        "battleship.api",
    ]

    for module in modules:
        assert importlib.import_module(module) is not None
