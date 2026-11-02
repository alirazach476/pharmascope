"""Unit tests for settings and package import."""

from __future__ import annotations

from pharmascope import __version__
from pharmascope.config.settings import Settings, clear_settings_cache


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_defaults(tmp_path, monkeypatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("PHARMASCOPE_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("PHARMASCOPE_DEV_RECORD_LIMIT", "250")
    monkeypatch.delenv("OPENFDA_API_KEY", raising=False)
    settings = Settings()
    assert settings.dev_record_limit == 250
    assert settings.openfda_api_key is None
    assert settings.cors_origins_list
    clear_settings_cache()
