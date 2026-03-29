"""
Rate Limiter — resilience-only retry wrapper for Gemini API calls.

Paid API tier: no inter-call pacing needed.
Retries only on genuine transient errors (503, network blips).
429s should be extremely rare on paid tier but handled gracefully.
"""
from __future__ import annotations

import random
import time
from typing import Any, Callable

from . import config


def throttled_call(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """
    Call fn(*args, **kwargs) with exponential-backoff retry on transient errors.
    No artificial pacing — paid API tier handles concurrent requests fine.
    """
    last_exc: Exception | None = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            exc_str = str(exc).lower()
            is_retryable = any(x in exc_str for x in [
                "429", "quota", "resource_exhausted",
                "503", "service unavailable", "overloaded",
                "too many requests", "connection",
            ])
            if not is_retryable or attempt == config.MAX_RETRIES:
                raise
            delay = min(
                config.RETRY_BASE_DELAY_SEC * (2 ** (attempt - 1)) + random.uniform(0, 2),
                config.RETRY_MAX_DELAY_SEC,
            )
            print(f"[Retry] Attempt {attempt}/{config.MAX_RETRIES} failed "
                  f"({exc.__class__.__name__}). Retrying in {delay:.1f}s...")
            time.sleep(delay)
    raise last_exc
