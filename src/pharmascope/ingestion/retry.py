"""HTTP retry helpers with exponential backoff and Retry-After support."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

from pharmascope.config.logging_config import get_logger

logger = get_logger("ingestion.retry")

T = TypeVar("T")

# Status codes that are generally safe to retry
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def compute_backoff_seconds(
    attempt: int,
    *,
    base: float = 1.0,
    cap: float = 60.0,
    retry_after: float | None = None,
) -> float:
    """Compute sleep duration with exponential backoff and full jitter.

    If ``Retry-After`` is provided (seconds), that value is preferred when larger
    than the computed backoff (still capped).
    """
    exp = min(cap, base * (2**attempt))
    jittered = random.uniform(0, exp)
    if retry_after is not None:
        return min(cap, max(jittered, retry_after))
    return jittered


def parse_retry_after(response: httpx.Response) -> float | None:
    """Parse Retry-After header as seconds when present and numeric."""
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        # HTTP-date form is uncommon for OpenFDA; skip parsing for simplicity
        logger.warning("Unparseable Retry-After header: %s", value)
        return None


def is_retryable(exc: BaseException | None, response: httpx.Response | None) -> bool:
    """Return True when the failure is considered transient."""
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return True
    if response is not None and response.status_code in RETRYABLE_STATUS_CODES:
        return True
    return False


def with_retries(
    operation: Callable[[], T],
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
    cap_delay: float = 60.0,
    operation_name: str = "http_request",
) -> T:
    """Execute ``operation`` with bounded retries for transient failures.

    Permanent client errors (4xx other than retryable codes) are not retried.
    """
    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        response: httpx.Response | None = None
        try:
            result = operation()
            # Allow callables that return Response for status-based retry
            if isinstance(result, httpx.Response):
                response = result
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt >= max_retries:
                        response.raise_for_status()
                    delay = compute_backoff_seconds(
                        attempt,
                        base=base_delay,
                        cap=cap_delay,
                        retry_after=parse_retry_after(response),
                    )
                    logger.warning(
                        "%s retryable status %s (attempt %s/%s); sleeping %.2fs",
                        operation_name,
                        response.status_code,
                        attempt + 1,
                        max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                if 400 <= response.status_code < 500:
                    response.raise_for_status()
            return result
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            response = exc.response
            if not is_retryable(exc, response) or attempt >= max_retries:
                raise
            delay = compute_backoff_seconds(
                attempt,
                base=base_delay,
                cap=cap_delay,
                retry_after=parse_retry_after(response) if response else None,
            )
            logger.warning(
                "%s HTTPStatusError (attempt %s/%s); sleeping %.2fs",
                operation_name,
                attempt + 1,
                max_retries + 1,
                delay,
            )
            time.sleep(delay)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            delay = compute_backoff_seconds(attempt, base=base_delay, cap=cap_delay)
            logger.warning(
                "%s network error %s (attempt %s/%s); sleeping %.2fs",
                operation_name,
                type(exc).__name__,
                attempt + 1,
                max_retries + 1,
                delay,
            )
            time.sleep(delay)

    assert last_exc is not None
    raise last_exc
