from pharmascope.ingestion.retry import compute_backoff_seconds, is_retryable
import httpx


def test_backoff_non_negative() -> None:
    for attempt in range(5):
        delay = compute_backoff_seconds(attempt, base=0.01, cap=1.0)
        assert 0 <= delay <= 1.0


def test_retry_after_preferred() -> None:
    delay = compute_backoff_seconds(0, base=0.01, cap=60.0, retry_after=5.0)
    assert delay >= 5.0


def test_is_retryable_timeout() -> None:
    assert is_retryable(httpx.TimeoutException("t"), None)
