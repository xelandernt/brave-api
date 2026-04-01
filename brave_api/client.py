import abc
import asyncio
import json
import os
import time
from typing import Any, AsyncIterator, Iterator, Optional, TypeVar

import niquests
from pydantic import BaseModel

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

    @staticmethod
    def _validate_response(
        model: type[ResponseModelT], payload: object
    ) -> ResponseModelT:
        return model.model_validate(payload)


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
        self, path: str, query: BaseModel, *, stream: bool = False
    ) -> Any:
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
            return response

        raise AssertionError("unreachable")

    async def _get(
        self, path: str, query: BaseModel, model: type[ResponseModelT]
    ) -> ResponseModelT:
        response = await self._request(path, query)
        return self._validate_response(model, response.json())

    async def search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        return await self.web_search(query)

    async def web_search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        return await self._get("/web/search", query, WebSearchApiResponse)

    async def image_search(self, query: ImageSearchAPIParams) -> ImageSearchApiResponse:
        return await self._get("/images/search", query, ImageSearchApiResponse)

    async def images(self, query: ImageSearchAPIParams) -> ImageSearchApiResponse:
        return await self.image_search(query)

    async def news_search(self, query: NewsSearchQueryParams) -> NewsSearchApiResponse:
        return await self._get("/news/search", query, NewsSearchApiResponse)

    async def news(self, query: NewsSearchQueryParams) -> NewsSearchApiResponse:
        return await self.news_search(query)

    async def video_search(
        self, query: VideoSearchQueryParams
    ) -> VideoSearchApiResponse:
        return await self._get("/videos/search", query, VideoSearchApiResponse)

    async def videos(self, query: VideoSearchQueryParams) -> VideoSearchApiResponse:
        return await self.video_search(query)

    async def spellcheck(self, query: SpellcheckQueryParams) -> SpellcheckApiResponse:
        return await self._get("/spellcheck/search", query, SpellcheckApiResponse)

    async def suggest(
        self, query: SuggestSearchQueryParams
    ) -> SuggestSearchApiResponse:
        return await self._get("/suggest/search", query, SuggestSearchApiResponse)

    async def suggest_search(
        self, query: SuggestSearchQueryParams
    ) -> SuggestSearchApiResponse:
        return await self.suggest(query)

    async def local_pois(
        self, query: LocalSearchQueryParams
    ) -> LocalPoiSearchApiResponse:
        return await self._get("/local/pois", query, LocalPoiSearchApiResponse)

    async def local_descriptions(
        self, query: LocalDescriptionsQueryParams
    ) -> LocalDescriptionsSearchApiResponse:
        return await self._get(
            "/local/descriptions", query, LocalDescriptionsSearchApiResponse
        )

    async def summarizer_search(
        self, query: SummarizerQueryParams
    ) -> SummarizerSearchApiResponse:
        return await self._get("/summarizer/search", query, SummarizerSearchApiResponse)

    async def summarizer_summary(
        self, query: SummarizerQueryParams
    ) -> SummarizerSummaryApiResponse:
        return await self._get(
            "/summarizer/summary", query, SummarizerSummaryApiResponse
        )

    async def summarizer_title(
        self, query: SummarizerQueryParams
    ) -> SummarizerTitleApiResponse:
        return await self._get("/summarizer/title", query, SummarizerTitleApiResponse)

    async def summarizer_enrichments(
        self, query: SummarizerQueryParams
    ) -> SummarizerEnrichmentsApiResponse:
        return await self._get(
            "/summarizer/enrichments", query, SummarizerEnrichmentsApiResponse
        )

    async def summarizer_followups(
        self, query: SummarizerQueryParams
    ) -> SummarizerFollowupsApiResponse:
        return await self._get(
            "/summarizer/followups", query, SummarizerFollowupsApiResponse
        )

    async def summarizer_entity_info(
        self, query: SummarizerEntityInfoQueryParams
    ) -> SummarizerEntityInfoApiResponse:
        return await self._get(
            "/summarizer/entity_info", query, SummarizerEntityInfoApiResponse
        )

    async def summarizer_summary_streaming(
        self, query: SummarizerQueryParams
    ) -> AsyncIterator[SummarizerStreamingEvent]:
        response = await self._request(
            "/summarizer/summary_streaming", query, stream=True
        )

        async for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if isinstance(line, bytes):
                yield _parse_streaming_event(line.decode())
            else:
                yield _parse_streaming_event(line)


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

    def _request(self, path: str, query: BaseModel, *, stream: bool = False) -> Any:
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
            return response

        raise AssertionError("unreachable")

    def _get(
        self, path: str, query: BaseModel, model: type[ResponseModelT]
    ) -> ResponseModelT:
        response = self._request(path, query)
        return self._validate_response(model, response.json())

    def search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        return self.web_search(query)

    def web_search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        return self._get("/web/search", query, WebSearchApiResponse)

    def image_search(self, query: ImageSearchAPIParams) -> ImageSearchApiResponse:
        return self._get("/images/search", query, ImageSearchApiResponse)

    def images(self, query: ImageSearchAPIParams) -> ImageSearchApiResponse:
        return self.image_search(query)

    def news_search(self, query: NewsSearchQueryParams) -> NewsSearchApiResponse:
        return self._get("/news/search", query, NewsSearchApiResponse)

    def news(self, query: NewsSearchQueryParams) -> NewsSearchApiResponse:
        return self.news_search(query)

    def video_search(self, query: VideoSearchQueryParams) -> VideoSearchApiResponse:
        return self._get("/videos/search", query, VideoSearchApiResponse)

    def videos(self, query: VideoSearchQueryParams) -> VideoSearchApiResponse:
        return self.video_search(query)

    def spellcheck(self, query: SpellcheckQueryParams) -> SpellcheckApiResponse:
        return self._get("/spellcheck/search", query, SpellcheckApiResponse)

    def suggest(self, query: SuggestSearchQueryParams) -> SuggestSearchApiResponse:
        return self._get("/suggest/search", query, SuggestSearchApiResponse)

    def suggest_search(
        self, query: SuggestSearchQueryParams
    ) -> SuggestSearchApiResponse:
        return self.suggest(query)

    def local_pois(self, query: LocalSearchQueryParams) -> LocalPoiSearchApiResponse:
        return self._get("/local/pois", query, LocalPoiSearchApiResponse)

    def local_descriptions(
        self, query: LocalDescriptionsQueryParams
    ) -> LocalDescriptionsSearchApiResponse:
        return self._get(
            "/local/descriptions", query, LocalDescriptionsSearchApiResponse
        )

    def summarizer_search(
        self, query: SummarizerQueryParams
    ) -> SummarizerSearchApiResponse:
        return self._get("/summarizer/search", query, SummarizerSearchApiResponse)

    def summarizer_summary(
        self, query: SummarizerQueryParams
    ) -> SummarizerSummaryApiResponse:
        return self._get("/summarizer/summary", query, SummarizerSummaryApiResponse)

    def summarizer_title(
        self, query: SummarizerQueryParams
    ) -> SummarizerTitleApiResponse:
        return self._get("/summarizer/title", query, SummarizerTitleApiResponse)

    def summarizer_enrichments(
        self, query: SummarizerQueryParams
    ) -> SummarizerEnrichmentsApiResponse:
        return self._get(
            "/summarizer/enrichments", query, SummarizerEnrichmentsApiResponse
        )

    def summarizer_followups(
        self, query: SummarizerQueryParams
    ) -> SummarizerFollowupsApiResponse:
        return self._get("/summarizer/followups", query, SummarizerFollowupsApiResponse)

    def summarizer_entity_info(
        self, query: SummarizerEntityInfoQueryParams
    ) -> SummarizerEntityInfoApiResponse:
        return self._get(
            "/summarizer/entity_info", query, SummarizerEntityInfoApiResponse
        )

    def summarizer_summary_streaming(
        self, query: SummarizerQueryParams
    ) -> Iterator[SummarizerStreamingEvent]:
        response = self._request("/summarizer/summary_streaming", query, stream=True)

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if isinstance(line, bytes):
                yield _parse_streaming_event(line.decode())
            else:
                yield _parse_streaming_event(line)
