import time

import httpx
from ollama import ResponseError

RETRYABLE_EXCEPTIONS = (httpx.TransportError, ResponseError)


def with_retry(fn, *args, retries: int = 3, backoff_seconds: float = 1.0, **kwargs):
    """Call fn(*args, **kwargs), retrying on transient Ollama/network errors.

    Ollama runs as a local service that can briefly refuse connections or time
    out (still loading a model, a dropped connection) - failing an entire
    ingest or query run on the first hiccup is needlessly brittle. Retries
    with exponential backoff before giving up and re-raising the last error.
    """
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except RETRYABLE_EXCEPTIONS:
            if attempt == retries - 1:
                raise
            time.sleep(backoff_seconds * (2**attempt))
