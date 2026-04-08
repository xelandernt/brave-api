import pytest
from pydantic import ValidationError

from brave_api.answers.models import AnswersRequest
from brave_api.image_search.models import ImageSearchAPIParams
from brave_api.llm_context.models import LLMContextQueryParams
from brave_api.local_search.models import (
    LocalDescriptionsQueryParams,
    LocalSearchQueryParams,
    PlaceSearchQueryParams,
)
from brave_api.news_search.models import NewsSearchQueryParams
from brave_api.suggest.models import SuggestSearchApiResponse, SuggestSearchQueryParams
from brave_api.util import (
    validate_date_range,
    validate_freshness,
    validate_result_filter,
    validate_location_ids,
)
from brave_api.video_search.models import VideoSearchQueryParams


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
    assert validate_date_range("2024-13-01to2024-01-31") is False
    assert validate_freshness(None) is None
    assert validate_freshness("") == ""
    assert validate_result_filter(None) is None

    with pytest.raises(ValueError):
        validate_result_filter(" , ")

    with pytest.raises(ValueError):
        validate_location_ids([])


def test_local_search_models_validate_ids_and_place_requirements() -> None:
    with pytest.raises(ValidationError):
        LocalSearchQueryParams(ids=[])

    with pytest.raises(ValidationError):
        LocalDescriptionsQueryParams(ids=["loc-1", "loc-1"])

    with pytest.raises(ValidationError):
        PlaceSearchQueryParams(q="coffee")

    with pytest.raises(ValidationError):
        PlaceSearchQueryParams(latitude=37.7749)

    params = PlaceSearchQueryParams(
        q="coffee",
        latitude=37.7749,
        longitude=-122.4194,
    )

    assert params.latitude == 37.7749
    assert params.longitude == -122.4194


def test_llm_context_and_answers_models_validate_inputs() -> None:
    with pytest.raises(ValidationError):
        LLMContextQueryParams(q="word " * 51)

    with pytest.raises(ValidationError):
        LLMContextQueryParams(q="python", freshness="bad")

    with pytest.raises(ValidationError):
        AnswersRequest(messages=[])
