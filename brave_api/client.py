import abc
import asyncio
import json
import os
import time
from typing import Any, Optional, TypeVar

import niquests
from pydantic import BaseModel

from brave_api import AsyncResponse, Response
from brave_api.constants import BRAVE_API_KEY_ENV_VAR
from brave_api.image_search.models import ImageSearchAPIParams, ImageSearchApiResponse
from brave_api.news_search.models import NewsSearchApiResponse, NewsSearchQueryParams
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
from brave_api.web_search.models import (
    LocalDescriptionsQueryParams,
    LocalDescriptionsSearchApiResponse,
    LocalPoiSearchApiResponse,
    LocalSearchQueryParams,
    WebSearchApiResponse,
    WebSearchQueryParams,
)
from brave_api.retries import RetryConfig

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


def _get_api_key_from_env() -> str | None:
    return os.getenv(BRAVE_API_KEY_ENV_VAR)


def _parse_streaming_event(line: str) -> SummarizerStreamingEvent:
    event: Optional[str] = None
    payload = line
    text: Optional[str] = None
    parsed_json: Optional[dict[str, Any]] = None

    if line.startswith("event:"):
        event = line.split(":", 1)[1].strip()
        payload = ""
    elif line.startswith("data:"):
        payload = line.split(":", 1)[1].strip()

    if payload:
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                parsed_json = data
                maybe_text = data.get("text") or data.get("content") or data.get("data")
                if isinstance(maybe_text, str):
                    text = maybe_text
            else:
                text = payload
        except json.JSONDecodeError:
            text = payload

    return SummarizerStreamingEvent(
        raw=line, event=event, text=text, payload_json=parsed_json
    )


class _BraveBase(abc.ABC):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        proxy: str | None = None,
        retry_config: RetryConfig | None = None,
    ):
        self.base_url = base_url or "https://api.search.brave.com/res/v1"
        self._provided_api_key = api_key
        self._proxy = proxy
        self._retry_config = retry_config

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _build_request(
        self, path: str, query_params: BaseModel
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        api_key = self._provided_api_key or _get_api_key_from_env()
        if not api_key:
            raise ValueError(
                "API key is required. Set it via environment variable BRAVE_API_KEY or pass it to the client."
            )

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }
        params = query_params.model_dump(exclude_none=True, exclude_unset=True)
        return self._build_url(path), headers, params


class AsyncBrave(_BraveBase):
    """Async Brave Search API client backed by `niquests.AsyncSession`."""

    def __init__(
        self,
        client: Optional[niquests.AsyncSession] = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        proxy: str | None = None,
        retry_config: RetryConfig | None = None,
    ):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            proxy=proxy,
            retry_config=retry_config,
        )
        self._client = client if client else niquests.AsyncSession()

    async def _request(
        self,
        path: str,
        query: BaseModel,
        *,
        stream: bool = False,
        response_model: type[ResponseModelT],
    ) -> AsyncResponse[ResponseModelT]:
        url, headers, query_params = self._build_request(path, query)
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(
                    url,
                    headers=headers,
                    params=query_params,
                    proxies=self._proxy,
                    stream=stream,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                await asyncio.sleep(
                    self._retry_config.strategy.get_delay(attempt, error=error)
                )
                continue

            if (
                self._retry_config is not None
                and attempt < attempts
                and self._retry_config.should_retry_status(response.status_code)
            ):
                await asyncio.sleep(
                    self._retry_config.strategy.get_delay(attempt, response=response)
                )
                continue

            response.raise_for_status()
            return AsyncResponse(response, response_model)

        raise AssertionError("unreachable")

    async def _get(
        self, path: str, query: BaseModel, model: type[ResponseModelT]
    ) -> AsyncResponse[ResponseModelT]:
        return await self._request(path, query, response_model=model)

    async def web_search(
        self, query: WebSearchQueryParams
    ) -> AsyncResponse[WebSearchApiResponse]:
        return await self._get("/web/search", query, WebSearchApiResponse)

    async def image_search(
        self, query: ImageSearchAPIParams
    ) -> AsyncResponse[ImageSearchApiResponse]:
        return await self._get("/images/search", query, ImageSearchApiResponse)

    async def news_search(
        self, query: NewsSearchQueryParams
    ) -> AsyncResponse[NewsSearchApiResponse]:
        return await self._get("/news/search", query, NewsSearchApiResponse)

    async def video_search(
        self, query: VideoSearchQueryParams
    ) -> AsyncResponse[VideoSearchApiResponse]:
        return await self._get("/videos/search", query, VideoSearchApiResponse)

    async def spellcheck(
        self, query: SpellcheckQueryParams
    ) -> AsyncResponse[SpellcheckApiResponse]:
        return await self._get("/spellcheck/search", query, SpellcheckApiResponse)

    async def suggest(
        self, query: SuggestSearchQueryParams
    ) -> AsyncResponse[SuggestSearchApiResponse]:
        return await self._get("/suggest/search", query, SuggestSearchApiResponse)

    async def local_pois(
        self, query: LocalSearchQueryParams
    ) -> AsyncResponse[LocalPoiSearchApiResponse]:
        return await self._get("/local/pois", query, LocalPoiSearchApiResponse)

    async def local_descriptions(
        self, query: LocalDescriptionsQueryParams
    ) -> AsyncResponse[LocalDescriptionsSearchApiResponse]:
        return await self._get(
            "/local/descriptions", query, LocalDescriptionsSearchApiResponse
        )

    async def summarizer_search(
        self, query: SummarizerQueryParams
    ) -> AsyncResponse[SummarizerSearchApiResponse]:
        return await self._get("/summarizer/search", query, SummarizerSearchApiResponse)

    async def summarizer_summary(
        self, query: SummarizerQueryParams
    ) -> AsyncResponse[SummarizerSummaryApiResponse]:
        return await self._get(
            "/summarizer/summary", query, SummarizerSummaryApiResponse
        )

    async def summarizer_title(
        self, query: SummarizerQueryParams
    ) -> AsyncResponse[SummarizerTitleApiResponse]:
        return await self._get("/summarizer/title", query, SummarizerTitleApiResponse)

    async def summarizer_enrichments(
        self, query: SummarizerQueryParams
    ) -> AsyncResponse[SummarizerEnrichmentsApiResponse]:
        return await self._get(
            "/summarizer/enrichments", query, SummarizerEnrichmentsApiResponse
        )

    async def summarizer_followups(
        self, query: SummarizerQueryParams
    ) -> AsyncResponse[SummarizerFollowupsApiResponse]:
        return await self._get(
            "/summarizer/followups", query, SummarizerFollowupsApiResponse
        )

    async def summarizer_entity_info(
        self, query: SummarizerEntityInfoQueryParams
    ) -> AsyncResponse[SummarizerEntityInfoApiResponse]:
        return await self._get(
            "/summarizer/entity_info", query, SummarizerEntityInfoApiResponse
        )

    async def summarizer_summary_streaming(
        self, query: SummarizerQueryParams
    ) -> AsyncResponse[SummarizerStreamingEvent]:
        return await self._request(
            "/summarizer/summary_streaming",
            query,
            stream=True,
            response_model=SummarizerStreamingEvent,
        )


class Brave(_BraveBase):
    """Synchronous Brave Search API client backed by `niquests.Session`."""

    def __init__(
        self,
        client: Optional[niquests.Session] = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        proxy: str | None = None,
        retry_config: RetryConfig | None = None,
    ):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            proxy=proxy,
            retry_config=retry_config,
        )
        self._client = client if client else niquests.Session()

    def _request(
        self,
        path: str,
        query: BaseModel,
        *,
        stream: bool = False,
        response_model: type[ResponseModelT],
    ) -> Response[ResponseModelT]:
        url, headers, query_params = self._build_request(path, query)
        attempts = self._retry_config.max_attempts if self._retry_config else 1
        retryable_exceptions = (
            self._retry_config.retryable_exceptions if self._retry_config else ()
        )

        for attempt in range(1, attempts + 1):
            try:
                response = self._client.get(
                    url,
                    headers=headers,
                    params=query_params,
                    proxies=self._proxy,
                    stream=stream,
                )
            except retryable_exceptions as error:
                if self._retry_config is None or attempt == attempts:
                    raise
                time.sleep(self._retry_config.strategy.get_delay(attempt, error=error))
                continue

            if (
                self._retry_config is not None
                and attempt < attempts
                and self._retry_config.should_retry_status(response.status_code)
            ):
                time.sleep(
                    self._retry_config.strategy.get_delay(attempt, response=response)
                )
                continue

            response.raise_for_status()
            return Response(response, response_model)

        raise AssertionError("unreachable")

    def _get(
        self, path: str, query: BaseModel, model: type[ResponseModelT]
    ) -> Response[ResponseModelT]:
        return self._request(path, query, response_model=model)

    def web_search(self, query: WebSearchQueryParams) -> Response[WebSearchApiResponse]:
        return self._get("/web/search", query, WebSearchApiResponse)

    def image_search(
        self, query: ImageSearchAPIParams
    ) -> Response[ImageSearchApiResponse]:
        return self._get("/images/search", query, ImageSearchApiResponse)

    def news_search(
        self, query: NewsSearchQueryParams
    ) -> Response[NewsSearchApiResponse]:
        return self._get("/news/search", query, NewsSearchApiResponse)

    def video_search(
        self, query: VideoSearchQueryParams
    ) -> Response[VideoSearchApiResponse]:
        return self._get("/videos/search", query, VideoSearchApiResponse)

    def spellcheck(
        self, query: SpellcheckQueryParams
    ) -> Response[SpellcheckApiResponse]:
        return self._get("/spellcheck/search", query, SpellcheckApiResponse)

    def suggest(
        self, query: SuggestSearchQueryParams
    ) -> Response[SuggestSearchApiResponse]:
        return self._get("/suggest/search", query, SuggestSearchApiResponse)

    def local_pois(
        self, query: LocalSearchQueryParams
    ) -> Response[LocalPoiSearchApiResponse]:
        return self._get("/local/pois", query, LocalPoiSearchApiResponse)

    def local_descriptions(
        self, query: LocalDescriptionsQueryParams
    ) -> Response[LocalDescriptionsSearchApiResponse]:
        return self._get(
            "/local/descriptions", query, LocalDescriptionsSearchApiResponse
        )

    def summarizer_search(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerSearchApiResponse]:
        return self._get("/summarizer/search", query, SummarizerSearchApiResponse)

    def summarizer_summary(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerSummaryApiResponse]:
        return self._get("/summarizer/summary", query, SummarizerSummaryApiResponse)

    def summarizer_title(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerTitleApiResponse]:
        return self._get("/summarizer/title", query, SummarizerTitleApiResponse)

    def summarizer_enrichments(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerEnrichmentsApiResponse]:
        return self._get(
            "/summarizer/enrichments", query, SummarizerEnrichmentsApiResponse
        )

    def summarizer_followups(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerFollowupsApiResponse]:
        return self._get("/summarizer/followups", query, SummarizerFollowupsApiResponse)

    def summarizer_entity_info(
        self, query: SummarizerEntityInfoQueryParams
    ) -> Response[SummarizerEntityInfoApiResponse]:
        return self._get(
            "/summarizer/entity_info", query, SummarizerEntityInfoApiResponse
        )

    def summarizer_summary_streaming(
        self, query: SummarizerQueryParams
    ) -> Response[SummarizerStreamingEvent]:
        return self._request(
            "/summarizer/summary_streaming",
            query,
            stream=True,
            response_model=SummarizerStreamingEvent,
        )
