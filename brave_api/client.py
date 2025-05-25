import abc
import os

from brave_api.constants import BRAVE_API_KEY_ENV_VAR
from brave_api.web_search.models import WebSearchApiResponse, WebSearchQueryParams

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


class AsyncBraveAPIClient(_BraveAPIClientBase):
    async def search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        url = self._build_search_url()
        api_key = self._provided_api_key or _get_api_key_from_env()
        if not api_key:
            raise ValueError(
                "API key is required. Set it via environment variable BRAVE_API_KEY or pass it to the client."
            )
        headers = {
            "X-Subscription-Token": api_key,
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=query.model_dump(exclude_unset=True)
            )

        response.raise_for_status()
        return WebSearchApiResponse.model_validate(response.json())


class BraveAPIClient(_BraveAPIClientBase):
    """
    A client for interacting with the Brave API.
    """

    def search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        url = self._build_search_url()
        api_key = self._provided_api_key or _get_api_key_from_env()
        if not api_key:
            raise ValueError(
                "API key is required. Set it via environment variable BRAVE_API_KEY or pass it to the client."
            )
        headers = {
            "X-Subscription-Token": api_key,
        }
        response = httpx.get(
            url=url, headers=headers, params=query.model_dump(exclude_unset=True)
        )
        response.raise_for_status()

        return WebSearchApiResponse.model_validate(response.json())
