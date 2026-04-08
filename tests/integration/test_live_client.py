import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import pytest
from niquests.exceptions import HTTPError

from brave_api.client import AsyncBrave, Brave
from brave_api.image_search.models import ImageSearchAPIParams
from brave_api.news_search.models import NewsSearchQueryParams
from brave_api.response import Response
from brave_api.spellcheck.models import SpellcheckQueryParams
from brave_api.suggest.models import SuggestSearchQueryParams
from brave_api.video_search.models import VideoSearchQueryParams
from brave_api.web_search.models import WebSearchQueryParams
from tests.conftest import live

T = TypeVar("T")

REQUEST_INTERVAL_SECONDS = 1.25

_last_request_started_at = 0.0


def _wait_for_request_slot() -> None:
    global _last_request_started_at

    elapsed = time.monotonic() - _last_request_started_at
    if elapsed < REQUEST_INTERVAL_SECONDS:
        time.sleep(REQUEST_INTERVAL_SECONDS - elapsed)
    _last_request_started_at = time.monotonic()


async def _wait_for_request_slot_async() -> None:
    global _last_request_started_at

    elapsed = time.monotonic() - _last_request_started_at
    if elapsed < REQUEST_INTERVAL_SECONDS:
        await asyncio.sleep(REQUEST_INTERVAL_SECONDS - elapsed)
    _last_request_started_at = time.monotonic()


def _is_plan_limited(error: HTTPError) -> bool:
    response = getattr(error, "response", None)
    if response is None or getattr(response, "status_code", None) != 400:
        return False

    try:
        payload = response.json()
    except ValueError:
        return False

    error_payload = payload.get("error")
    return (
        isinstance(error_payload, dict)
        and error_payload.get("code") == "OPTION_NOT_IN_PLAN"
    )


def _is_rate_limited(error: HTTPError) -> bool:
    return getattr(error.response, "status_code", None) == 429


def _handle_live_http_error(error: HTTPError) -> None:
    if _is_plan_limited(error):
        pytest.skip("Live API plan does not include this endpoint")
    if _is_rate_limited(error):
        pytest.skip("Live API rate limit exceeded during test run")
    raise error


def _call_sync(func: Callable[..., T], *args: object) -> T:
    _wait_for_request_slot()
    return func(*args)


async def _call_async(func: Callable[..., Awaitable[T]], *args: object) -> T:
    await _wait_for_request_slot_async()
    return await func(*args)


def _assert_sync_type(
    func: Callable[..., object],
    query: object,
    expected_type: str,
) -> None:
    try:
        response = _call_sync(func, query)
        assert isinstance(response, Response)
        assert getattr(response.parsed_data, "type") == expected_type
    except HTTPError as error:
        _handle_live_http_error(error)


async def _assert_async_type(
    func: Callable[..., Awaitable[object]],
    query: object,
    expected_type: str,
) -> None:
    try:
        response = await _call_async(func, query)
        assert isinstance(response, Response)
        assert getattr(response.parsed_data, "type") == expected_type
    except HTTPError as error:
        _handle_live_http_error(error)


@pytest.fixture(scope="module")
def live_client() -> Brave:
    return Brave()


@pytest.fixture
def async_live_client() -> AsyncBrave:
    return AsyncBrave()


@live
def test_sync_web_search(live_client: Brave) -> None:
    _assert_sync_type(
        live_client.web_search,
        WebSearchQueryParams(q="open source privacy tools", count=3),
        "search",
    )


@live
def test_sync_image_search(live_client: Brave) -> None:
    _assert_sync_type(
        live_client.image_search,
        ImageSearchAPIParams(q="golden retriever", count=2),
        "images",
    )


@live
def test_sync_news_search(live_client: Brave) -> None:
    _assert_sync_type(
        live_client.news_search, NewsSearchQueryParams(q="technology", count=2), "news"
    )


@live
def test_sync_video_search(live_client: Brave) -> None:
    _assert_sync_type(
        live_client.video_search,
        VideoSearchQueryParams(q="python tutorial", count=2),
        "videos",
    )


@live
def test_sync_spellcheck(live_client: Brave) -> None:
    _assert_sync_type(
        live_client.spellcheck, SpellcheckQueryParams(q="pythn"), "spellcheck"
    )


@live
def test_sync_suggest(live_client: Brave) -> None:
    _assert_sync_type(
        live_client.suggest, SuggestSearchQueryParams(q="python", count=3), "suggest"
    )


@live
async def test_async_web_search(async_live_client: AsyncBrave) -> None:
    await _assert_async_type(
        async_live_client.web_search,
        WebSearchQueryParams(q="open source browsers", count=3),
        "search",
    )


@live
async def test_async_image_search(async_live_client: AsyncBrave) -> None:
    await _assert_async_type(
        async_live_client.image_search,
        ImageSearchAPIParams(q="forest trail", count=2),
        "images",
    )


@live
async def test_async_news_search(async_live_client: AsyncBrave) -> None:
    await _assert_async_type(
        async_live_client.news_search,
        NewsSearchQueryParams(q="space exploration", count=2),
        "news",
    )


@live
async def test_async_video_search(async_live_client: AsyncBrave) -> None:
    await _assert_async_type(
        async_live_client.video_search,
        VideoSearchQueryParams(q="golang tutorial", count=2),
        "videos",
    )


@live
async def test_async_spellcheck(async_live_client: AsyncBrave) -> None:
    await _assert_async_type(
        async_live_client.spellcheck,
        SpellcheckQueryParams(q="javascript"),
        "spellcheck",
    )


@live
async def test_async_suggest(async_live_client: AsyncBrave) -> None:
    await _assert_async_type(
        async_live_client.suggest,
        SuggestSearchQueryParams(q="docke", count=3),
        "suggest",
    )
