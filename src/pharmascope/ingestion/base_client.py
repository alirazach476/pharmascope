"""Base HTTP client for official pharmaceutical data APIs."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import yaml

from pharmascope.config.logging_config import get_logger
from pharmascope.config.settings import Settings, get_settings
from pharmascope.ingestion.retry import with_retries

logger = get_logger("ingestion.base_client")


class BaseAPIClient:
    """Shared HTTP behaviour for documented official APIs."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(self.settings.openfda_timeout_seconds),
            headers={"User-Agent": "PharmaScope/0.1.0 (research; +local)"},
            follow_redirects=True,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> BaseAPIClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def load_source_registry(self) -> dict[str, Any]:
        path = self.settings.sources_config_path()
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data.get("sources", {})

    def get_source_config(self, short_name: str) -> dict[str, Any]:
        sources = self.load_source_registry()
        if short_name not in sources:
            raise KeyError(f"Unknown source '{short_name}' in sources.yaml")
        return sources[short_name]

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform an HTTP request with retries and return parsed JSON."""
        correlation_id = correlation_id or str(uuid4())
        headers = {"X-Request-ID": correlation_id}

        def _do() -> httpx.Response:
            logger.debug(
                "HTTP %s %s params=%s correlation_id=%s",
                method,
                url,
                params,
                correlation_id,
            )
            response = self._client.request(method, url, params=params, headers=headers)
            return response

        response = with_retries(
            _do,
            max_retries=self.settings.openfda_max_retries,
            operation_name=f"{method} {url}",
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object from {url}, got {type(payload)}")
        return payload
