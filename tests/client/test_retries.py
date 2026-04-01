import niquests
import pytest

from brave_api.client import AsyncBrave, Brave
from brave_api.retries import (
    ExponentialBackoffRetryStrategy,
    FixedDelayRetryStrategy,
    RetryAfterRetryStrategy,
    RetryConfig,
)
from brave_api.web_search.models import WebSearchQueryParams
from tests.client.fakes import (
    FakeAsyncResponse,
    FakeAsyncSession,
    FakeResponse,
    FakeSession,
)


def test_default_sync_client_does_not_retry() -> None:
    session = FakeSession([FakeResponse(status_code=503)])
    client = Brave(api_key="token", client=session)

    with pytest.raises(niquests.exceptions.HTTPError):
        client.search(WebSearchQueryParams(q="python"))

    assert len(session.calls) == 1


def test_retry_sync_client_retries_retryable_status() -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=503),
            FakeResponse({"type": "search"}),
        ]
    )
    client = Brave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = client.search(WebSearchQueryParams(q="python"))

    assert response.type == "search"
    assert len(session.calls) == 2


def test_retry_sync_client_retries_connection_errors() -> None:
    session = FakeSession(
        [
            niquests.exceptions.ConnectionError("boom"),
            FakeResponse({"type": "search"}),
        ]
    )
    client = Brave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = client.search(WebSearchQueryParams(q="python"))

    assert response.type == "search"
    assert len(session.calls) == 2


def test_retry_sync_client_uses_retry_after_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=429, headers={"Retry-After": "3"}),
            FakeResponse({"type": "search"}),
        ]
    )
    client = Brave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2,
            strategy=RetryAfterRetryStrategy(
                fallback_strategy=ExponentialBackoffRetryStrategy(
                    base_delay_seconds=0.0,
                    max_delay_seconds=0.0,
                )
            ),
        ),
    )
    delays: list[float] = []
    monkeypatch.setattr("brave_api.client.time.sleep", delays.append)

    response = client.search(WebSearchQueryParams(q="python"))

    assert response.type == "search"
    assert delays == [3.0]


async def test_default_async_client_does_not_retry() -> None:
    session = FakeAsyncSession([FakeAsyncResponse(status_code=503)])
    client = AsyncBrave(api_key="token", client=session)

    with pytest.raises(niquests.exceptions.HTTPError):
        await client.search(WebSearchQueryParams(q="python"))

    assert len(session.calls) == 1


async def test_retry_async_client_retries_retryable_status() -> None:
    session = FakeAsyncSession(
        [
            FakeAsyncResponse(status_code=503),
            FakeAsyncResponse({"type": "search"}),
        ]
    )
    client = AsyncBrave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = await client.search(WebSearchQueryParams(q="python"))

    assert response.type == "search"
    assert len(session.calls) == 2


async def test_retry_async_client_retries_connection_errors() -> None:
    session = FakeAsyncSession(
        [
            niquests.exceptions.ConnectionError("boom"),
            FakeAsyncResponse({"type": "search"}),
        ]
    )
    client = AsyncBrave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = await client.search(WebSearchQueryParams(q="python"))

    assert response.type == "search"
    assert len(session.calls) == 2
