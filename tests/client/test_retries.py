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
    FakeResponse,
    AsyncGetStub,
    SyncGetStub,
)


def test_default_sync_client_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    session = niquests.Session()
    get = SyncGetStub([FakeResponse(status_code=503)])
    monkeypatch.setattr(session, "get", get)
    client = Brave(api_key="token", client=session)

    with pytest.raises(niquests.exceptions.HTTPError):
        client.web_search(WebSearchQueryParams(q="python"))

    assert len(get.calls) == 1


def test_retry_sync_client_retries_retryable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    get = SyncGetStub(
        [
            FakeResponse(status_code=503),
            FakeResponse({"type": "search"}),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    client = Brave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = client.web_search(WebSearchQueryParams(q="python"))

    assert response.parsed_data.type == "search"
    assert len(get.calls) == 2


def test_retry_sync_client_retries_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    get = SyncGetStub(
        [
            niquests.exceptions.ConnectionError("boom"),
            FakeResponse({"type": "search"}),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    client = Brave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = client.web_search(WebSearchQueryParams(q="python"))

    assert response.parsed_data.type == "search"
    assert len(get.calls) == 2


def test_retry_sync_client_uses_retry_after_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    get = SyncGetStub(
        [
            FakeResponse(status_code=429, headers={"Retry-After": "3"}),
            FakeResponse({"type": "search"}),
        ]
    )
    monkeypatch.setattr(session, "get", get)
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

    response = client.web_search(WebSearchQueryParams(q="python"))

    assert response.parsed_data.type == "search"
    assert delays == [3.0]


async def test_default_async_client_does_not_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    get = AsyncGetStub([FakeResponse(status_code=503)])
    monkeypatch.setattr(session, "get", get)
    client = AsyncBrave(api_key="token", client=session)

    with pytest.raises(niquests.exceptions.HTTPError):
        await client.web_search(WebSearchQueryParams(q="python"))

    assert len(get.calls) == 1


async def test_retry_async_client_retries_retryable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    get = AsyncGetStub(
        [
            FakeResponse(status_code=503),
            FakeResponse({"type": "search"}),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    client = AsyncBrave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = await client.web_search(WebSearchQueryParams(q="python"))

    assert response.parsed_data.type == "search"
    assert len(get.calls) == 2


async def test_retry_async_client_retries_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    get = AsyncGetStub(
        [
            niquests.exceptions.ConnectionError("boom"),
            FakeResponse({"type": "search"}),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    client = AsyncBrave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2, strategy=FixedDelayRetryStrategy(delay_seconds=0.0)
        ),
    )

    response = await client.web_search(WebSearchQueryParams(q="python"))

    assert response.parsed_data.type == "search"
    assert len(get.calls) == 2
