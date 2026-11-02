"""Validated application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_project_root() -> Path:
    """Resolve project root as the directory containing pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


class Settings(BaseSettings):
    """Runtime configuration for PharmaScope.

    Secrets and machine-specific paths come from environment variables or a
    local ``.env`` file. Never hardcode credentials in source.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    pharmascope_env: str = Field(default="development", alias="PHARMASCOPE_ENV")
    pharmascope_log_level: str = Field(default="INFO", alias="PHARMASCOPE_LOG_LEVEL")
    data_root: Path = Field(default=Path("./data"), alias="PHARMASCOPE_DATA_ROOT")
    config_dir: Path = Field(default=Path("./configs"), alias="PHARMASCOPE_CONFIG_DIR")
    project_root: Path = Field(default_factory=_default_project_root)

    # OpenFDA
    openfda_api_key: str | None = Field(default=None, alias="OPENFDA_API_KEY")
    openfda_base_url: str = Field(default="https://api.fda.gov", alias="OPENFDA_BASE_URL")
    openfda_timeout_seconds: float = Field(default=60.0, alias="OPENFDA_TIMEOUT_SECONDS")
    openfda_max_retries: int = Field(default=5, alias="OPENFDA_MAX_RETRIES")
    openfda_default_limit: int = Field(default=100, alias="OPENFDA_DEFAULT_LIMIT")
    openfda_max_concurrency: int = Field(default=2, alias="OPENFDA_MAX_CONCURRENCY")

    # Extraction bounds
    dev_record_limit: int = Field(default=1000, alias="PHARMASCOPE_DEV_RECORD_LIMIT")
    allow_full_download: bool = Field(default=False, alias="PHARMASCOPE_ALLOW_FULL_DOWNLOAD")

    # Warehouse
    duckdb_path: Path = Field(
        default=Path("./data/metadata/pharmascope.duckdb"),
        alias="DUCKDB_PATH",
    )

    # Optional PostgreSQL
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="pharmascope", alias="POSTGRES_DB")
    postgres_user: str = Field(default="pharmascope", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_cors_origins: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501",
        alias="API_CORS_ORIGINS",
    )

    @field_validator("data_root", "config_dir", "duckdb_path", mode="before")
    @classmethod
    def _coerce_path(cls, value: object) -> Path:
        return Path(str(value))

    @field_validator("openfda_api_key", mode="before")
    @classmethod
    def _empty_str_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    def resolve_data_root(self) -> Path:
        path = self.data_root
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def resolve_config_dir(self) -> Path:
        path = self.config_dir
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def resolve_duckdb_path(self) -> Path:
        path = self.duckdb_path
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def layer_path(self, layer: str) -> Path:
        """Return absolute path for a medallion layer directory."""
        return self.resolve_data_root() / layer

    def sources_config_path(self) -> Path:
        return self.resolve_config_dir() / "sources.yaml"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful in tests)."""
    get_settings.cache_clear()
