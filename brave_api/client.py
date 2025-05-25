import os

from brave_api.web_search.models import WebSearchApiResponse, WebSearchQueryParams

import httpx


def _get_api_key_from_env() -> str | None:
    return os.getenv("BRAVE_API_KEY")


class BraveAPIClient:
    """
    A client for interacting with the Brave API.
    """

    def __init__(self, base_url: str | None, api_key: str | None = None):
        self.base_url = base_url or "https://api.search.brave.com/res/v1"
        self._provided_api_key = api_key

    def search(self, query: WebSearchQueryParams) -> WebSearchApiResponse:
        url = f"{self.base_url}/web/search"
        headers = {
            "X-Subscription-Token": self._provided_api_key or _get_api_key_from_env(),
        }
        response = httpx.get(url=url, headers=headers, params=query.model_dump())

        response.raise_for_status()

        return WebSearchApiResponse.model_validate(response.json())
