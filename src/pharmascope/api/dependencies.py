"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from pharmascope.config.settings import Settings, get_settings
from pharmascope.warehouse.connection import DuckDBWarehouse


def settings_dep() -> Settings:
    return get_settings()


def warehouse_dep() -> Generator[DuckDBWarehouse, None, None]:
    wh = DuckDBWarehouse(get_settings(), read_only=True)
    try:
        wh.connect()
        yield wh
    finally:
        wh.close()
