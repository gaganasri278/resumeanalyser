"""Tests for the process-local analysis rate limiter."""

from app.utils.rate_limiter import AnalysisRateLimiter


def test_rate_limiter_enforces_sliding_window(monkeypatch) -> None:
    """Requests are denied until the configured time window expires."""
    current_time = [10.0]
    monkeypatch.setattr(
        "app.utils.rate_limiter.time.monotonic", lambda: current_time[0]
    )
    limiter = AnalysisRateLimiter(max_requests=1, max_concurrent=1, window_seconds=5)

    assert limiter.try_acquire()
    limiter.release()
    assert not limiter.try_acquire()

    current_time[0] = 15.0
    assert limiter.try_acquire()
    limiter.release()


def test_rate_limiter_enforces_concurrency() -> None:
    """Concurrent work is denied while all execution slots are occupied."""
    limiter = AnalysisRateLimiter(max_requests=5, max_concurrent=1)

    assert limiter.try_acquire()
    assert not limiter.try_acquire()

    limiter.release()
    assert limiter.try_acquire()
    limiter.release()
