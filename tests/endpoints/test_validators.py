import pytest
from pydantic import ValidationError

from brave_api.image_search.models import ImageSearchAPIParams
from brave_api.news_search.models import NewsSearchQueryParams
from brave_api.suggest.models import SuggestSearchApiResponse, SuggestSearchQueryParams
from brave_api.video_search.models import VideoSearchQueryParams
from brave_api.web_search.models import (
    _validate_date_range,
    _validate_freshness,
    _validate_location_ids,
    _validate_result_filter,
)


def test_image_search_validators_reject_invalid_word_count_and_country() -> None:
    with pytest.raises(ValidationError):
        ImageSearchAPIParams(q="word " * 51)

    with pytest.raises(ValidationError):
        ImageSearchAPIParams(q="cat", country="USA")


def test_news_and_video_validators_reject_invalid_country_codes() -> None:
    with pytest.raises(ValidationError):
        NewsSearchQueryParams(q="climate", country="USA")

    with pytest.raises(ValidationError):
        VideoSearchQueryParams(q="tutorial", country="USA")

    assert VideoSearchQueryParams(q="tutorial", country="ALL").country == "ALL"


def test_suggest_validators_reject_invalid_inputs_and_type() -> None:
    with pytest.raises(ValidationError):
        SuggestSearchQueryParams(q="word " * 51)

    with pytest.raises(ValueError):
        SuggestSearchQueryParams.country_code_length("USA")
    assert SuggestSearchQueryParams.country_code_length("US") == "US"

    with pytest.raises(ValueError):
        SuggestSearchQueryParams.lang_min_length("e")
    assert SuggestSearchQueryParams.lang_min_length("en") == "en"

    with pytest.raises(ValueError):
        SuggestSearchApiResponse.type_must_be_suggest("search")
    assert SuggestSearchApiResponse.type_must_be_suggest("suggest") == "suggest"


def test_web_search_helper_validators_cover_optional_and_error_paths() -> None:
    assert _validate_date_range("2024-13-01to2024-01-31") is False
    assert _validate_freshness(None) is None
    assert _validate_freshness("") == ""
    assert _validate_result_filter(None) is None

    with pytest.raises(ValueError):
        _validate_result_filter(" , ")

    with pytest.raises(ValueError):
        _validate_location_ids([])
