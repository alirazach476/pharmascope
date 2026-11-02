"""Filesystem helpers for medallion data directories."""

from __future__ import annotations

from pathlib import Path

from pharmascope.config.settings import Settings, get_settings

LAYER_NAMES = ("raw", "bronze", "silver", "gold", "quarantine", "metadata")


def ensure_layer_dirs(settings: Settings | None = None) -> dict[str, Path]:
    """Create medallion layer directories and return their absolute paths."""
    settings = settings or get_settings()
    root = settings.resolve_data_root()
    paths: dict[str, Path] = {}
    for name in LAYER_NAMES:
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        paths[name] = path
    # Synthetic fixtures are separate and must never mix with authentic layers
    fixtures = root / "synthetic_test_fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    paths["synthetic_test_fixtures"] = fixtures
    return paths
