import pytest

from brave_api.web_search.models import WebSearchApiResponse
from pydantic import ValidationError


def test_search_response_does_not_validate() -> None:
    with pytest.raises(ValidationError):
        WebSearchApiResponse()  # type: ignore[call-arg]
