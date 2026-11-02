"""Structured logging configuration for PharmaScope."""

from __future__ import annotations

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import yaml

from pharmascope.config.settings import Settings, get_settings


def setup_logging(
    settings: Settings | None = None,
    *,
    log_file: Path | None = None,
) -> None:
    """Configure application logging from YAML or a sensible default.

    Parameters
    ----------
    settings:
        Optional settings instance. Uses ``get_settings()`` when omitted.
    log_file:
        Optional override for the rotating file handler path.
    """
    settings = settings or get_settings()
    config_path = settings.resolve_config_dir() / "logging.yaml"

    if config_path.exists():
        with config_path.open(encoding="utf-8") as fh:
            config: dict[str, Any] = yaml.safe_load(fh)

        # Ensure log directory exists when file handler is configured
        handlers = config.get("handlers", {})
        file_handler = handlers.get("file")
        if file_handler and "filename" in file_handler:
            filename = Path(log_file) if log_file else Path(file_handler["filename"])
            if not filename.is_absolute():
                filename = settings.project_root / filename
            filename.parent.mkdir(parents=True, exist_ok=True)
            file_handler["filename"] = str(filename)

        # Apply configured log level
        level = settings.pharmascope_log_level.upper()
        if "root" in config:
            config["root"]["level"] = level
        if "loggers" in config and "pharmascope" in config["loggers"]:
            config["loggers"]["pharmascope"]["level"] = level

        logging.config.dictConfig(config)
    else:
        logging.basicConfig(
            level=getattr(logging, settings.pharmascope_log_level.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger under the pharmascope namespace."""
    if not name.startswith("pharmascope"):
        name = f"pharmascope.{name}"
    return logging.getLogger(name)
