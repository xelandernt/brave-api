from __future__ import annotations

import abc
import asyncio
import json
import os
import time
from collections.abc import Callable
from typing import TypeVar

import niquests
from pydantic import BaseModel

from brave_api.answers.models import (
    AnswersApiResponse,
    AnswersRequest,
    AnswersStreamingEvent,
)
from brave_api.constants import BRAVE_API_KEY_ENV_VAR
from brave_api.image_search.models import ImageSearchAPIParams, ImageSearchApiResponse
from brave_api.llm_context.models import LLMContextApiResponse, LLMContextQueryParams
from brave_api.local_search.models import (
    LocalDescriptionsQueryParams,
    LocalDescriptionsSearchApiResponse,
    LocalPoiSearchApiResponse,
    LocalSearchQueryParams,
    PlaceSearchApiResponse,
    PlaceSearchQueryParams,
)
from brave_api.news_search.models import NewsSearchApiResponse, NewsSearchQueryParams
from brave_api.response import AsyncResponse, Response
from brave_api.retries import RetryConfig
from brave_api.rich_search.models import RichSearchApiResponse, RichSearchQueryParams
from brave_api.spellcheck.models import SpellcheckApiResponse, SpellcheckQueryParams
from brave_api.suggest.models import SuggestSearchApiResponse, SuggestSearchQueryParams
from brave_api.summarizer_search.models import (
    SummarizerEnrichmentsApiResponse,
    SummarizerEntityInfoApiResponse,
    SummarizerEntityInfoQueryParams,
    SummarizerFollowupsApiResponse,
    SummarizerQueryParams,
    SummarizerSearchApiResponse,
    SummarizerStreamingEvent,
    SummarizerSummaryApiResponse,
    SummarizerTitleApiResponse,
)
from brave_api.video_search.models import VideoSearchApiResponse, VideoSearchQueryParams
from brave_api.web_search.models import WebSearchApiResponse, WebSearchQueryParams

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)

HeadersMap = dict[str, str]
JsonObject = dict[str, object]
ProxyConfig = dict[str, str]
QueryParamValue = str | list[str] | None
QueryParams = dict[str, QueryParamValue]


def _get_api_key_from_env() -> str | None:
    return os.getenv(BRAVE_API_KEY_ENV_VAR)


def _coerce_json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None

    payload: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"JSON object keys must be strings, got {type(key)!r}")
        payload[key] = _coerce_json_value(item)
    return payload


def _coerce_json_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_coerce_json_value(item) for item in value]

    parsed_object = _coerce_json_object(value)
    if parsed_object is not None:
        return parsed_object

    raise TypeError(f"Unsupported JSON value type: {type(value)!r}")


def _normalize_query_item(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    raise TypeError(f"Unsupported query list item type: {type(value)!r}")


def _normalize_query_value(value: object) -> QueryParamValue:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, list):
        return [_normalize_query_item(item) for item in value]
    raise TypeError(f"Unsupported query parameter type: {type(value)!r}")


def _parse_streaming_event(line: str) -> SummarizerStreamingEvent:
    event: str | None = None
    payload = line
    text: str | None = None
    parsed_json: JsonObject | None = None

    if line.startswith("event:"):
        event = line.split(":", 1)[1].strip()
        payload = ""
    elif line.startswith("data:"):
        payload = line.split(":", 1)[1].strip()

    if payload:
        try:
            loaded_payload: object = json.loads(payload)
        except json.JSONDecodeError:
            text = payload
        else:
            parsed_json = _coerce_json_object(loaded_payload)
            if parsed_json is not None:
                maybe_text = (
                    parsed_json.get("text")
                    or parsed_json.get("content")
                    or parsed_json.get("data")
                )
                if isinstance(maybe_text, str):
                    text = maybe_text
            else:
                text = payload

    return SummarizerStreamingEvent(
        raw=line,
        event=event,
        text=text,
        payload_json=parsed_json,
    )


def _extract_answers_text(response: AnswersApiResponse) -> str | None:
    if not response.choices:
        return None

    first_choice = response.choices[0]
    if first_choice.delta is not None and isinstance(first_choice.delta.content, str):
        return first_choice.delta.content
    if first_choice.message is not None and isinstance(
        first_choice.message.content, str
    ):
        return first_choice.message.content
    return None


def _parse_answers_streaming_event(line: str) -> AnswersStreamingEvent:
    event: str | None = None
    payload = line
    text: str | None = None
    done = False
    chunk: AnswersApiResponse | None = None

    if line.startswith("event:"):
        event = line.split(":", 1)[1].strip()
        payload = ""
    elif line.startswith("data:"):
        payload = line.split(":", 1)[1].strip()

    if payload:
        if payload == "[DONE]":
            done = True
        else:
            try:
                loaded_payload: object = json.loads(payload)
            except json.JSONDecodeError:
                text = payload
            else:
                parsed_object = _coerce_json_object(loaded_payload)
                if parsed_object is not None:
                    chunk = AnswersApiResponse.model_validate(parsed_object)
                    text = _extract_answers_text(chunk)
                else:
                    text = payload

    return AnswersStreamingEvent(
        raw=line,
        event=event,
        text=text,
        done=done,
        chunk=chunk,
    )


class _BraveBase(abc.ABC):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        proxy: str | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.base_url = base_url or "https://api.search.brave.com/res/v1"
        self._provided_api_key = api_key
        self._proxy = proxy
        self._retry_config = retry_config

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _build_request(
        self, path: str, query_params: BaseModel
    ) -> tuple[str, HeadersMap, QueryParams]:
        api_key = self._provided_api_key or _get_api_key_from_env()
        if not api_key:
            raise ValueError(
                "API key is required. Set it via environment variable BRAVE_API_KEY or pass it to the client."
            )

        headers: HeadersMap = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }
        params: QueryParams = {}
        for key, value in query_params.model_dump(
            exclude_none=True,
            exclude_unset=True,
        ).items():
            params[key] = _normalize_query_value(value)
        return self._build_url(path), headers, params

    def _build_json_request(
        self, path: str, payload_model: BaseModel
    ) -> tuple[str, HeadersMap, JsonObject]:
        api_key = self._provided_api_key or _get_api_key_from_env()
        if not api_key:
            raise ValueError(
                "API key is required. Set it via environment variable BRAVE_API_KEY or pass it to the client."
            )

        headers: HeadersMap = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Subscription-Token": api_key,
        }
        payload = _coerce_json_object(
            payload_model.model_dump(
                exclude_none=True,
                exclude_unset=True,
            )
        )
        if payload is None:
            raise TypeError("Request body must serialize to a JSON object")
        return self._build_url(path), headers, payload

    def _build_proxies(self) -> ProxyConfig | None:
        if self._proxy is None:
            return None
        return {
            "http": self._proxy,
            "https": self._proxy,
        }

    def _should_retry_status(
        self, status_code: int | None, attempt: int, attempts: int
    ) -> bool:
        return (
            self._retry_config is not None
            and attempt < attempts
            and status_code is not None
            and self._retry_config.should_retry_status(status_code)
        )


class AsyncBrave(_BraveBase):
    """Async Brave Search API client backed by `niquests.AsyncSession`."""

    def __init__(
        self,
        client: niquests.AsyncSession | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        proxy: str | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            proxy=proxy,
            retry_config=retry_config,
        )
        self._client = client if client is not None else niquests.AsyncSession()

    async def _request(
        self,
        path: str,
        query: BaseModel,
        response_model: type[ResponseModelT],
    ) -> Response[ResponseModelT]:
        url, headers, query_params = self._build_request(path, query)
        proxies = self._build_proxies()
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response: niquests.Response = await self._client.get(
                    url,
                    headers=headers,
                    params=query_params,
                    proxies=proxies,
                    stream=False,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                await asyncio.sleep(
                    self._retry_config.strategy.get_delay(attempt, error=error)
                )
                continue

            retry_config = self._retry_config
            if retry_config is not None and self._should_retry_status(
                response.status_code,
                attempt,
                attempts,
            ):
                await asyncio.sleep(
                    retry_config.strategy.get_delay(attempt, response=response)
                )
                continue

            response.raise_for_status()
            return Response(response, response_model)

        raise AssertionError("unreachable")

    async def _request_streaming(
        self,
        path: str,
        query: BaseModel,
        response_model: type[ResponseModelT],
        *,
        line_parser: Callable[[str], ResponseModelT] | None = None,
    ) -> AsyncResponse[ResponseModelT]:
        url, headers, query_params = self._build_request(path, query)
        proxies = self._build_proxies()
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response: niquests.AsyncResponse = await self._client.get(
                    url,
                    headers=headers,
                    params=query_params,
                    proxies=proxies,
                    stream=True,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                await asyncio.sleep(
                    self._retry_config.strategy.get_delay(attempt, error=error)
                )
                continue

            retry_config = self._retry_config
            if retry_config is not None and self._should_retry_status(
                response.status_code,
                attempt,
                attempts,
            ):
                await asyncio.sleep(
                    retry_config.strategy.get_delay(attempt, response=response)
                )
                continue

            response.raise_for_status()
            return AsyncResponse(
                response,
                response_model,
                line_parser=line_parser,
            )

        raise AssertionError("unreachable")

    async def _request_json(
        self,
        path: str,
        payload_model: BaseModel,
        response_model: type[ResponseModelT],
    ) -> Response[ResponseModelT]:
        url, headers, payload = self._build_json_request(path, payload_model)
        proxies = self._build_proxies()
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response: niquests.Response = await self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                    proxies=proxies,
                    stream=False,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                await asyncio.sleep(
                    self._retry_config.strategy.get_delay(attempt, error=error)
                )
                continue

            retry_config = self._retry_config
            if retry_config is not None and self._should_retry_status(
                response.status_code,
                attempt,
                attempts,
            ):
                await asyncio.sleep(
                    retry_config.strategy.get_delay(attempt, response=response)
                )
                continue

            response.raise_for_status()
            return Response(response, response_model)

        raise AssertionError("unreachable")

    async def _request_json_streaming(
        self,
        path: str,
        payload_model: BaseModel,
        response_model: type[ResponseModelT],
        *,
        line_parser: Callable[[str], ResponseModelT] | None = None,
    ) -> AsyncResponse[ResponseModelT]:
        url, headers, payload = self._build_json_request(path, payload_model)
        proxies = self._build_proxies()
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response: niquests.AsyncResponse = await self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                    proxies=proxies,
                    stream=True,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                await asyncio.sleep(
                    self._retry_config.strategy.get_delay(attempt, error=error)
                )
                continue

            retry_config = self._retry_config
            if retry_config is not None and self._should_retry_status(
                response.status_code,
                attempt,
                attempts,
            ):
                await asyncio.sleep(
                    retry_config.strategy.get_delay(attempt, response=response)
                )
                continue

            response.raise_for_status()
            return AsyncResponse(
                response,
                response_model,
                line_parser=line_parser,
            )

        raise AssertionError("unreachable")

    async def web_search(
        self, query: WebSearchQueryParams
    ) -> Response[WebSearchApiResponse]:
        return await self._request("/web/search", query, WebSearchApiResponse)

    async def rich_search(
        self, query: RichSearchQueryParams
    ) -> Response[RichSearchApiResponse]:
        return await self._request("/web/rich", query, RichSearchApiResponse)

    async def image_search(
        self, query: ImageSearchAPIParams
    ) -> Response[ImageSearchApiResponse]:
        return await self._request("/images/search", query, ImageSearchApiResponse)

    async def news_search(
        self, query: NewsSearchQueryParams
    ) -> Response[NewsSearchApiResponse]:
        return await self._request("/news/search", query, NewsSearchApiResponse)

    async def video_search(
        self, query: VideoSearchQueryParams
    ) -> Response[VideoSearchApiResponse]:
        return await self._request("/videos/search", query, VideoSearchApiResponse)

    async def spellcheck(
        self, query: SpellcheckQueryParams
    ) -> Response[SpellcheckApiResponse]:
        return await self._request("/spellcheck/search", query, SpellcheckApiResponse)

    async def suggest(
        self, query: SuggestSearchQueryParams
    ) -> Response[SuggestSearchApiResponse]:
        return await self._request("/suggest/search", query, SuggestSearchApiResponse)

    async def local_pois(
        self, query: LocalSearchQueryParams
    ) -> Response[LocalPoiSearchApiResponse]:
        return await self._request("/local/pois", query, LocalPoiSearchApiResponse)

    async def place_search(
        self, query: PlaceSearchQueryParams
    ) -> Response[PlaceSearchApiResponse]:
        return await self._request("/local/place_search", query, PlaceSearchApiResponse)

    async def local_descriptions(
        self, query: LocalDescriptionsQueryParams
    ) -> Response[LocalDescriptionsSearchApiResponse]:
        return await self._request(
            "/local/descriptions",
            query,
            LocalDescriptionsSearchApiResponse,
        )

    async def summarizer_search(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerSearchApiResponse]:
        return await self._request(
            "/summarizer/search", query, SummarizerSearchApiResponse
        )

    async def llm_context(
        self, query: LLMContextQueryParams
    ) -> Response[LLMContextApiResponse]:
        return await self._request("/llm/context", query, LLMContextApiResponse)

    async def answers(self, query: AnswersRequest) -> Response[AnswersApiResponse]:
        return await self._request_json(
            "/chat/completions",
            query.model_copy(update={"stream": False}),
            AnswersApiResponse,
        )

    async def answers_streaming(
        self, query: AnswersRequest
    ) -> AsyncResponse[AnswersStreamingEvent]:
        return await self._request_json_streaming(
            "/chat/completions",
            query.model_copy(update={"stream": True}),
            AnswersStreamingEvent,
            line_parser=_parse_answers_streaming_event,
        )

    async def summarizer_summary(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerSummaryApiResponse]:
        return await self._request(
            "/summarizer/summary",
            query,
            SummarizerSummaryApiResponse,
        )

    async def summarizer_title(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerTitleApiResponse]:
        return await self._request(
            "/summarizer/title", query, SummarizerTitleApiResponse
        )

    async def summarizer_enrichments(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerEnrichmentsApiResponse]:
        return await self._request(
            "/summarizer/enrichments",
            query,
            SummarizerEnrichmentsApiResponse,
        )

    async def summarizer_followups(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerFollowupsApiResponse]:
        return await self._request(
            "/summarizer/followups",
            query,
            SummarizerFollowupsApiResponse,
        )

    async def summarizer_entity_info(
        self, query: SummarizerEntityInfoQueryParams
    ) -> Response[SummarizerEntityInfoApiResponse]:
        return await self._request(
            "/summarizer/entity_info",
            query,
            SummarizerEntityInfoApiResponse,
        )

    async def summarizer_summary_streaming(
        self, query: SummarizerQueryParams
    ) -> AsyncResponse[SummarizerStreamingEvent]:
        return await self._request_streaming(
            "/summarizer/summary_streaming",
            query,
            SummarizerStreamingEvent,
            line_parser=_parse_streaming_event,
        )


class Brave(_BraveBase):
    """Synchronous Brave Search API client backed by `niquests.Session`."""

    def __init__(
        self,
        client: niquests.Session | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        proxy: str | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            proxy=proxy,
            retry_config=retry_config,
        )
        self._client = client if client is not None else niquests.Session()

    def _request(
        self,
        path: str,
        query: BaseModel,
        *,
        stream: bool = False,
        response_model: type[ResponseModelT],
        line_parser: Callable[[str], ResponseModelT] | None = None,
    ) -> Response[ResponseModelT]:
        url, headers, query_params = self._build_request(path, query)
        proxies = self._build_proxies()
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response: niquests.Response = self._client.get(
                    url,
                    headers=headers,
                    params=query_params,
                    proxies=proxies,
                    stream=stream,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                time.sleep(self._retry_config.strategy.get_delay(attempt, error=error))
                continue

            retry_config = self._retry_config
            if retry_config is not None and self._should_retry_status(
                response.status_code,
                attempt,
                attempts,
            ):
                time.sleep(retry_config.strategy.get_delay(attempt, response=response))
                continue

            response.raise_for_status()
            return Response(
                response,
                response_model,
                line_parser=line_parser,
            )

        raise AssertionError("unreachable")

    def _request_json(
        self,
        path: str,
        payload_model: BaseModel,
        *,
        stream: bool = False,
        response_model: type[ResponseModelT],
        line_parser: Callable[[str], ResponseModelT] | None = None,
    ) -> Response[ResponseModelT]:
        url, headers, payload = self._build_json_request(path, payload_model)
        proxies = self._build_proxies()
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response: niquests.Response = self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                    proxies=proxies,
                    stream=stream,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                time.sleep(self._retry_config.strategy.get_delay(attempt, error=error))
                continue

            retry_config = self._retry_config
            if retry_config is not None and self._should_retry_status(
                response.status_code,
                attempt,
                attempts,
            ):
                time.sleep(retry_config.strategy.get_delay(attempt, response=response))
                continue

            response.raise_for_status()
            return Response(
                response,
                response_model,
                line_parser=line_parser,
            )

        raise AssertionError("unreachable")

    def web_search(self, query: WebSearchQueryParams) -> Response[WebSearchApiResponse]:
        return self._request("/web/search", query, response_model=WebSearchApiResponse)

    def rich_search(
        self, query: RichSearchQueryParams
    ) -> Response[RichSearchApiResponse]:
        return self._request("/web/rich", query, response_model=RichSearchApiResponse)

    def image_search(
        self, query: ImageSearchAPIParams
    ) -> Response[ImageSearchApiResponse]:
        return self._request(
            "/images/search",
            query,
            response_model=ImageSearchApiResponse,
        )

    def news_search(
        self, query: NewsSearchQueryParams
    ) -> Response[NewsSearchApiResponse]:
        return self._request(
            "/news/search", query, response_model=NewsSearchApiResponse
        )

    def video_search(
        self, query: VideoSearchQueryParams
    ) -> Response[VideoSearchApiResponse]:
        return self._request(
            "/videos/search",
            query,
            response_model=VideoSearchApiResponse,
        )

    def spellcheck(
        self, query: SpellcheckQueryParams
    ) -> Response[SpellcheckApiResponse]:
        return self._request(
            "/spellcheck/search",
            query,
            response_model=SpellcheckApiResponse,
        )

    def suggest(
        self, query: SuggestSearchQueryParams
    ) -> Response[SuggestSearchApiResponse]:
        return self._request(
            "/suggest/search", query, response_model=SuggestSearchApiResponse
        )

    def local_pois(
        self, query: LocalSearchQueryParams
    ) -> Response[LocalPoiSearchApiResponse]:
        return self._request(
            "/local/pois", query, response_model=LocalPoiSearchApiResponse
        )

    def place_search(
        self, query: PlaceSearchQueryParams
    ) -> Response[PlaceSearchApiResponse]:
        return self._request(
            "/local/place_search",
            query,
            response_model=PlaceSearchApiResponse,
        )

    def local_descriptions(
        self, query: LocalDescriptionsQueryParams
    ) -> Response[LocalDescriptionsSearchApiResponse]:
        return self._request(
            "/local/descriptions",
            query,
            response_model=LocalDescriptionsSearchApiResponse,
        )

    def summarizer_search(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerSearchApiResponse]:
        return self._request(
            "/summarizer/search",
            query,
            response_model=SummarizerSearchApiResponse,
        )

    def llm_context(
        self, query: LLMContextQueryParams
    ) -> Response[LLMContextApiResponse]:
        return self._request(
            "/llm/context",
            query,
            response_model=LLMContextApiResponse,
        )

    def answers(self, query: AnswersRequest) -> Response[AnswersApiResponse]:
        return self._request_json(
            "/chat/completions",
            query.model_copy(update={"stream": False}),
            response_model=AnswersApiResponse,
        )

    def answers_streaming(
        self, query: AnswersRequest
    ) -> Response[AnswersStreamingEvent]:
        return self._request_json(
            "/chat/completions",
            query.model_copy(update={"stream": True}),
            stream=True,
            response_model=AnswersStreamingEvent,
            line_parser=_parse_answers_streaming_event,
        )

    def summarizer_summary(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerSummaryApiResponse]:
        return self._request(
            "/summarizer/summary",
            query,
            response_model=SummarizerSummaryApiResponse,
        )

    def summarizer_title(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerTitleApiResponse]:
        return self._request(
            "/summarizer/title",
            query,
            response_model=SummarizerTitleApiResponse,
        )

    def summarizer_enrichments(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerEnrichmentsApiResponse]:
        return self._request(
            "/summarizer/enrichments",
            query,
            response_model=SummarizerEnrichmentsApiResponse,
        )

    def summarizer_followups(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerFollowupsApiResponse]:
        return self._request(
            "/summarizer/followups",
            query,
            response_model=SummarizerFollowupsApiResponse,
        )

    def summarizer_entity_info(
        self, query: SummarizerEntityInfoQueryParams
    ) -> Response[SummarizerEntityInfoApiResponse]:
        return self._request(
            "/summarizer/entity_info",
            query,
            response_model=SummarizerEntityInfoApiResponse,
        )

    def summarizer_summary_streaming(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerStreamingEvent]:
        return self._request(
            "/summarizer/summary_streaming",
            query,
            stream=True,
            response_model=SummarizerStreamingEvent,
            line_parser=_parse_streaming_event,
        )
