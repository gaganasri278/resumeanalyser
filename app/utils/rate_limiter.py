"""Process-local request rate and concurrency guard."""

import threading
import time
from collections import deque


class AnalysisRateLimiter:
    """Limit total request starts and concurrent analyses in this process."""

    def __init__(
        self,
        max_requests: int,
        max_concurrent: int,
        window_seconds: float = 60.0,
    ) -> None:
        """Initialize the sliding-window limiter and concurrency semaphore."""
        if max_requests < 1 or max_concurrent < 1 or window_seconds <= 0:
            raise ValueError("Rate limiter limits and window must be positive.")

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._request_times: deque[float] = deque()
        self._lock = threading.Lock()
        self._concurrency = threading.BoundedSemaphore(max_concurrent)

    def try_acquire(self) -> bool:
        """Reserve a request slot, returning false when capacity is exhausted."""
        now = time.monotonic()
        with self._lock:
            while (
                self._request_times
                and now - self._request_times[0] >= self._window_seconds
            ):
                self._request_times.popleft()

            if len(self._request_times) >= self._max_requests:
                return False
            if not self._concurrency.acquire(blocking=False):
                return False

            self._request_times.append(now)
            return True

    def release(self) -> None:
        """Release a previously acquired concurrent analysis slot."""
        self._concurrency.release()
