import abc
import os
import typing
from types import TracebackType
from typing import Optional

from brave_api.constants import BRAVE_API_KEY_ENV_VAR
from brave_api.web_search.models import WebSearchApiResponse, WebSearchQueryParams
from contextlib import AbstractAsyncContextManager
import httpx


def _get_api_key_from_env() -> str | None:
    return os.getenv(BRAVE_API_KEY_ENV_VAR)


class _BraveAPIClientBase(abc.ABC):
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        proxy: str | None = None,
    ):
        self.base_url = base_url or "https://api.search.brave.com/res/v1"
        self._provided_api_key = api_key
        self._proxy = proxy

    def _build_search_url(self) -> str:
        return f"{self.base_url}/web/search"

    def _build_search_params(
        self, query_params: WebSearchQueryParams
    ) -> tuple[str, dict[str, str], dict[str, typing.Any]]:
        url = self._build_search_url()
        api_key = self._provided_api_key or _get_api_key_from_env()
        if not api_key:
            raise ValueError(
                "API key is required. Set it via environment variable BRAVE_API_KEY or pass it to the client."
            )
        headers = {
            "X-Subscription-Token": api_key,
        }
        return url, headers, query_params.model_dump(exclude_unset=True)


class AsyncBraveAPIClient(
    _BraveAPIClientBase, AbstractAsyncContextManager["AsyncBraveAPIClient"]
):
    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        *args: typing.Any,
        **kwargs: typing.Any,
    ):
        super().__init__(*args, **kwargs)
        self._client = client if client else httpx.AsyncClient()
        self._transport: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "AsyncBraveAPIClient":
        self._transport = await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        self._transport = None
        await self._client.aclose()

    def _verify_transport(self) -> None:
        if self._transport is None:
            raise RuntimeError("Use async with `AsyncBraveAPIClient()`")

    async def search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        self._verify_transport()
        url, headers, query_params = self._build_search_params(query)
        response = await self._transport.get(  # type: ignore[union-attr]
            url, headers=headers, params=query_params
        )

        response.raise_for_status()
        return WebSearchApiResponse.model_validate(response.json())


class BraveAPIClient(_BraveAPIClientBase):
    """
    A client for interacting with the Brave API.
    """

    def search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        url, headers, query_params = self._build_search_params(query)
        response = httpx.get(url=url, headers=headers, params=query_params)
        response.raise_for_status()

        return WebSearchApiResponse.model_validate(response.json())
