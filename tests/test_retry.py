import httpx
import pytest
from ollama import ResponseError

from rag.retry import with_retry


def test_with_retry_returns_result_on_first_success():
    assert with_retry(lambda: 42) == 42


def test_with_retry_recovers_after_transient_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ConnectError("connection refused")
        return "ok"

    assert with_retry(flaky, retries=3, backoff_seconds=0) == "ok"
    assert len(calls) == 3


def test_with_retry_reraises_after_exhausting_retries():
    def always_fails():
        raise ResponseError("model not found")

    with pytest.raises(ResponseError):
        with_retry(always_fails, retries=2, backoff_seconds=0)


def test_with_retry_does_not_catch_unrelated_exceptions():
    def broken():
        raise ValueError("not a transient error")

    with pytest.raises(ValueError):
        with_retry(broken, retries=3, backoff_seconds=0)
