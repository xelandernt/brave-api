import niquests
import pytest

from brave_api.client import AsyncBrave, Brave
from brave_api.retries import (
    BraveRateLimitRetryStrategy,
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


def test_default_sync_client_retries_retryable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    get = SyncGetStub([FakeResponse(status_code=503), FakeResponse({"type": "search"})])
    monkeypatch.setattr(session, "get", get)
    client = Brave(api_key="token", client=session)

    response = client.web_search(WebSearchQueryParams(q="python"))

    assert response.parsed_data.type == "search"
    assert len(get.calls) == 2


def test_sync_client_can_disable_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    session = niquests.Session()
    get = SyncGetStub([FakeResponse(status_code=503)])
    monkeypatch.setattr(session, "get", get)
    client = Brave(api_key="token", client=session, retry_config=None)

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


def test_retry_sync_client_uses_brave_rate_limit_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    get = SyncGetStub(
        [
            FakeResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Remaining": "0, 14000",
                    "X-RateLimit-Reset": "1, 1234567",
                },
            ),
            FakeResponse({"type": "search"}),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    client = Brave(
        api_key="token",
        client=session,
        retry_config=RetryConfig(
            max_attempts=2,
            strategy=BraveRateLimitRetryStrategy(
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
    assert delays == [1.0]


def test_brave_rate_limit_retry_strategy_waits_for_exhausted_quota_window() -> None:
    delay = BraveRateLimitRetryStrategy._parse_brave_rate_limit_delay(
        {
            "X-RateLimit-Remaining": "1, 0",
            "X-RateLimit-Reset": "1, 42",
        }
    )

    assert delay == 42.0


def test_brave_rate_limit_retry_strategy_ignores_malformed_headers() -> None:
    delay = BraveRateLimitRetryStrategy._parse_brave_rate_limit_delay(
        {
            "X-RateLimit-Remaining": "0, 1",
            "X-RateLimit-Reset": "1; 42",
        }
    )

    assert delay is None


async def test_default_async_client_retries_retryable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    get = AsyncGetStub(
        [FakeResponse(status_code=503), FakeResponse({"type": "search"})]
    )
    monkeypatch.setattr(session, "get", get)
    client = AsyncBrave(api_key="token", client=session)

    response = await client.web_search(WebSearchQueryParams(q="python"))

    assert response.parsed_data.type == "search"
    assert len(get.calls) == 2


async def test_async_client_can_disable_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    get = AsyncGetStub([FakeResponse(status_code=503)])
    monkeypatch.setattr(session, "get", get)
    client = AsyncBrave(api_key="token", client=session, retry_config=None)

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
