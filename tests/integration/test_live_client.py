import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import pytest
from niquests.exceptions import HTTPError

from brave_api.answers.models import AnswersApiResponse, AnswersRequest
from brave_api.client import AsyncBrave, Brave
from brave_api.image_search.models import ImageSearchAPIParams
from brave_api.llm_context.models import LLMContextQueryParams
from brave_api.local_search.models import (
    LocalDescriptionsQueryParams,
    LocalSearchQueryParams,
    PlaceSearchApiResponse,
    PlaceSearchQueryParams,
)
from brave_api.response import Response
from brave_api.rich_search.models import RichSearchQueryParams
from brave_api.news_search.models import NewsSearchQueryParams
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


async def _is_plan_limited_async(error: HTTPError) -> bool:
    response = getattr(error, "response", None)
    if response is None or getattr(response, "status_code", None) != 400:
        return False

    try:
        payload = response.json()
        if inspect.isawaitable(payload):
            payload = await payload
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


async def _handle_live_http_error_async(error: HTTPError) -> None:
    if await _is_plan_limited_async(error):
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


def _call_sync_live(func: Callable[..., T], *args: object) -> T:
    try:
        return _call_sync(func, *args)
    except HTTPError as error:
        _handle_live_http_error(error)
        raise AssertionError("unreachable")


async def _call_async_live(func: Callable[..., Awaitable[T]], *args: object) -> T:
    try:
        return await _call_async(func, *args)
    except HTTPError as error:
        await _handle_live_http_error_async(error)
        raise AssertionError("unreachable")


def _assert_sync_type(
    func: Callable[..., object],
    query: object,
    expected_type: str,
) -> None:
    response = _call_sync_live(func, query)
    assert isinstance(response, Response)
    assert getattr(response.parsed_data, "type") == expected_type


async def _assert_async_type(
    func: Callable[..., Awaitable[object]],
    query: object,
    expected_type: str,
) -> None:
    response = await _call_async_live(func, query)
    assert isinstance(response, Response)
    assert getattr(response.parsed_data, "type") == expected_type


def _answers_response_has_content(response: AnswersApiResponse) -> bool:
    for choice in response.choices:
        message_content = choice.message.content if choice.message is not None else None
        delta_content = choice.delta.content if choice.delta is not None else None
        if message_content or delta_content:
            return True
    return False


def _first_location_id_from_place_search(
    response: Response[PlaceSearchApiResponse],
) -> str:
    assert response.parsed_data.type == "locations"
    results = response.parsed_data.results or []
    for result in results:
        if result.id:
            return result.id
    pytest.skip("Live place search did not return a reusable location id")


def _get_sync_rich_callback_key(live_client: Brave) -> str:
    response = _call_sync_live(
        live_client.web_search,
        WebSearchQueryParams(q="weather in london", count=1, enable_rich_callback=True),
    )
    rich = response.parsed_data.rich
    if rich is None or rich.hint is None:
        pytest.skip("Live web search did not return a rich callback hint")
    return rich.hint.callback_key


async def _get_async_rich_callback_key(async_live_client: AsyncBrave) -> str:
    response = await _call_async_live(
        async_live_client.web_search,
        WebSearchQueryParams(q="weather in london", count=1, enable_rich_callback=True),
    )
    rich = response.parsed_data.rich
    if rich is None or rich.hint is None:
        pytest.skip("Live web search did not return a rich callback hint")
    return rich.hint.callback_key


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
def test_sync_rich_search(live_client: Brave) -> None:
    callback_key = _get_sync_rich_callback_key(live_client)
    _assert_sync_type(
        live_client.rich_search,
        RichSearchQueryParams(callback_key=callback_key),
        "rich",
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
        live_client.news_search,
        NewsSearchQueryParams(q="technology", count=2),
        "news",
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
def test_sync_place_and_local_endpoints(live_client: Brave) -> None:
    place_response = _call_sync_live(
        live_client.place_search,
        PlaceSearchQueryParams(
            q="coffee",
            latitude=37.7749,
            longitude=-122.4194,
            radius=2000,
            count=5,
        ),
    )
    assert place_response.parsed_data.type == "locations"

    location_id = _first_location_id_from_place_search(place_response)
    _assert_sync_type(
        live_client.local_pois,
        LocalSearchQueryParams(ids=[location_id]),
        "local_pois",
    )
    _assert_sync_type(
        live_client.local_descriptions,
        LocalDescriptionsQueryParams(ids=[location_id]),
        "local_descriptions",
    )


@live
def test_sync_llm_context(live_client: Brave) -> None:
    response = _call_sync_live(
        live_client.llm_context,
        LLMContextQueryParams(q="open source browsers", count=3),
    )
    assert response.parsed_data.grounding.generic


@live
def test_sync_answers(live_client: Brave) -> None:
    response = _call_sync_live(
        live_client.answers,
        AnswersRequest(
            model="brave",
            messages=[
                {
                    "role": "user",
                    "content": "What is the second highest mountain?",
                }
            ],
        ),
    )
    assert _answers_response_has_content(response.parsed_data)


@live
def test_sync_answers_streaming(live_client: Brave) -> None:
    response = _call_sync_live(
        live_client.answers_streaming,
        AnswersRequest(
            model="brave",
            messages=[{"role": "user", "content": "What is 2+2?"}],
        ),
    )

    saw_text = False
    for index, event in enumerate(response.iter_lines_parsed()):
        if event.text:
            saw_text = True
            break
        if event.done or index >= 50:
            break

    assert saw_text


@live
async def test_async_web_search(async_live_client: AsyncBrave) -> None:
    await _assert_async_type(
        async_live_client.web_search,
        WebSearchQueryParams(q="open source browsers", count=3),
        "search",
    )


@live
async def test_async_rich_search(async_live_client: AsyncBrave) -> None:
    callback_key = await _get_async_rich_callback_key(async_live_client)
    await _assert_async_type(
        async_live_client.rich_search,
        RichSearchQueryParams(callback_key=callback_key),
        "rich",
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


@live
async def test_async_place_and_local_endpoints(async_live_client: AsyncBrave) -> None:
    place_response = await _call_async_live(
        async_live_client.place_search,
        PlaceSearchQueryParams(
            q="coffee",
            latitude=37.7749,
            longitude=-122.4194,
            radius=2000,
            count=5,
        ),
    )
    assert place_response.parsed_data.type == "locations"

    location_id = _first_location_id_from_place_search(place_response)
    await _assert_async_type(
        async_live_client.local_pois,
        LocalSearchQueryParams(ids=[location_id]),
        "local_pois",
    )
    await _assert_async_type(
        async_live_client.local_descriptions,
        LocalDescriptionsQueryParams(ids=[location_id]),
        "local_descriptions",
    )


@live
async def test_async_llm_context(async_live_client: AsyncBrave) -> None:
    response = await _call_async_live(
        async_live_client.llm_context,
        LLMContextQueryParams(q="open source browsers", count=3),
    )
    assert response.parsed_data.grounding.generic


@live
async def test_async_answers(async_live_client: AsyncBrave) -> None:
    response = await _call_async_live(
        async_live_client.answers,
        AnswersRequest(
            model="brave",
            messages=[
                {
                    "role": "user",
                    "content": "What is the second highest mountain?",
                }
            ],
        ),
    )
    assert _answers_response_has_content(response.parsed_data)


@live
async def test_async_answers_streaming(async_live_client: AsyncBrave) -> None:
    response = await _call_async_live(
        async_live_client.answers_streaming,
        AnswersRequest(
            model="brave",
            messages=[{"role": "user", "content": "What is 2+2?"}],
        ),
    )

    saw_text = False
    index = 0
    async for event in response.iter_lines_parsed():
        if event.text:
            saw_text = True
            break
        if event.done or index >= 50:
            break
        index += 1

    assert saw_text
