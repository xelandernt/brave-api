import niquests
import pytest
from pydantic import ValidationError

from brave_api.client import AsyncBrave, Brave
from brave_api.image_search.models import ImageSearchAPIParams
from brave_api.news_search.models import NewsSearchApiResponse, NewsSearchQueryParams
from brave_api.spellcheck.models import SpellcheckQueryParams, SpellcheckApiResponse
from brave_api.suggest.models import SuggestSearchQueryParams
from brave_api.summarizer_search.models import (
    SummarizerEntityInfoQueryParams,
    SummarizerQueryParams,
    SummarizerSearchApiResponse,
)
from brave_api.video_search.models import VideoSearchQueryParams
from brave_api.web_search.models import (
    LocalDescriptionsQueryParams,
    LocalSearchQueryParams,
    WebSearchQueryParams,
    WebSearchApiResponse,
)
from tests.client.fakes import (
    AsyncGetStub,
    FakeAsyncResponse,
    FakeResponse,
    SyncGetStub,
    image_payload,
    news_payload,
    suggest_payload,
    video_payload,
)


def test_sync_client_methods_use_expected_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    get = SyncGetStub(
        [
            FakeResponse({"type": "search"}),
            FakeResponse(image_payload()),
            FakeResponse(news_payload()),
            FakeResponse(video_payload()),
            FakeResponse(
                {
                    "type": "spellcheck",
                    "query": {"original": "helo"},
                    "results": [{"query": "hello"}],
                }
            ),
            FakeResponse(suggest_payload()),
            FakeResponse({"type": "local_pois", "results": []}),
            FakeResponse({"type": "local_descriptions", "results": []}),
            FakeResponse(
                {"status": "complete", "title": "Summary", "summary": "Hello"}
            ),
            FakeResponse({"status": "complete", "summary": "Hello"}),
            FakeResponse({"status": "complete", "title": "Summary"}),
            FakeResponse(
                {"status": "complete", "enrichments": {"raw_summary": "Hello"}}
            ),
            FakeResponse({"status": "complete", "followups": ["Next question"]}),
            FakeResponse(
                {
                    "status": "complete",
                    "entities_info": [{"name": "K2", "type": "Mountain"}],
                }
            ),
            FakeResponse(lines=["event: message", 'data: {"text":"chunk"}']),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    client = Brave(api_key="token", client=session, proxy="http://proxy")

    assert client.web_search(WebSearchQueryParams(q="python")).parsed_data.type == (
        "search"
    )
    assert client.image_search(ImageSearchAPIParams(q="cat")).parsed_data.type == (
        "images"
    )
    assert client.news_search(NewsSearchQueryParams(q="climate")).parsed_data.type == (
        "news"
    )
    assert (
        client.video_search(VideoSearchQueryParams(q="tutorial")).parsed_data.type
        == "videos"
    )
    assert client.spellcheck(SpellcheckQueryParams(q="helo")).parsed_data.type == (
        "spellcheck"
    )
    assert client.suggest(SuggestSearchQueryParams(q="pyth")).parsed_data.type == (
        "suggest"
    )
    assert client.local_pois(
        LocalSearchQueryParams(ids=["loc-1"])
    ).parsed_data.type == ("local_pois")
    assert (
        client.local_descriptions(
            LocalDescriptionsQueryParams(ids=["loc-1"])
        ).parsed_data.type
        == "local_descriptions"
    )
    assert (
        client.summarizer_search(SummarizerQueryParams(key="k")).parsed_data.title
        == "Summary"
    )
    assert (
        client.summarizer_summary(SummarizerQueryParams(key="k")).parsed_data.summary
        == "Hello"
    )
    assert (
        client.summarizer_title(SummarizerQueryParams(key="k")).parsed_data.title
        == "Summary"
    )
    enrichments_response = client.summarizer_enrichments(
        SummarizerQueryParams(key="k")
    ).parsed_data
    assert enrichments_response.enrichments is not None
    assert enrichments_response.enrichments.raw_summary == "Hello"
    assert client.summarizer_followups(
        SummarizerQueryParams(key="k")
    ).parsed_data.followups == ["Next question"]
    entity_info_response = client.summarizer_entity_info(
        SummarizerEntityInfoQueryParams(key="k")
    ).parsed_data
    assert entity_info_response.entities_info is not None
    assert entity_info_response.entities_info[0].name == "K2"
    stream = list(
        client.summarizer_summary_streaming(
            SummarizerQueryParams(key="k")
        ).iter_lines_parsed()
    )
    assert stream[0].event == "message"
    assert stream[1].text == "chunk"

    assert [call["url"] for call in get.calls] == [
        "https://api.search.brave.com/res/v1/web/search",
        "https://api.search.brave.com/res/v1/images/search",
        "https://api.search.brave.com/res/v1/news/search",
        "https://api.search.brave.com/res/v1/videos/search",
        "https://api.search.brave.com/res/v1/spellcheck/search",
        "https://api.search.brave.com/res/v1/suggest/search",
        "https://api.search.brave.com/res/v1/local/pois",
        "https://api.search.brave.com/res/v1/local/descriptions",
        "https://api.search.brave.com/res/v1/summarizer/search",
        "https://api.search.brave.com/res/v1/summarizer/summary",
        "https://api.search.brave.com/res/v1/summarizer/title",
        "https://api.search.brave.com/res/v1/summarizer/enrichments",
        "https://api.search.brave.com/res/v1/summarizer/followups",
        "https://api.search.brave.com/res/v1/summarizer/entity_info",
        "https://api.search.brave.com/res/v1/summarizer/summary_streaming",
    ]
    assert all(
        call["headers"] is not None
        and call["headers"]["X-Subscription-Token"] == "token"
        for call in get.calls
    )
    assert all(
        call["proxies"] == {"http": "http://proxy", "https": "http://proxy"}
        for call in get.calls
    )
    assert get.calls[-1]["stream"] is True


async def test_async_client_methods_and_streaming_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    get = AsyncGetStub(
        [
            FakeResponse({"type": "search"}),
            FakeResponse(
                {"type": "spellcheck", "query": {"original": "helo"}, "results": []}
            ),
            FakeAsyncResponse(lines=['data: {"text":"async chunk"}']),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    client = AsyncBrave(api_key="token", client=session)

    web_response = await client.web_search(WebSearchQueryParams(q="python"))
    spellcheck_response = await client.spellcheck(SpellcheckQueryParams(q="helo"))
    stream_response = await client.summarizer_summary_streaming(
        SummarizerQueryParams(key="k")
    )
    stream = [event async for event in stream_response.iter_lines_parsed()]

    assert web_response.parsed_data.type == "search"
    assert spellcheck_response.parsed_data.type == "spellcheck"
    assert stream[0].text == "async chunk"
    assert get.calls[0]["url"] == "https://api.search.brave.com/res/v1/web/search"
    assert get.calls[2]["stream"] is True


def test_news_search_query_params_validate_freshness() -> None:
    params = NewsSearchQueryParams(q="climate summit", freshness="pw", country="ALL")

    assert params.freshness == "pw"
    assert params.country == "ALL"


def test_video_search_query_params_reject_invalid_freshness() -> None:
    with pytest.raises(ValidationError):
        VideoSearchQueryParams(q="tutorial", freshness="yesterday")


def test_spellcheck_query_params_enforce_query_limit() -> None:
    with pytest.raises(ValidationError):
        SpellcheckQueryParams(q="word " * 51)


def test_spellcheck_response_parses() -> None:
    response = SpellcheckApiResponse.model_validate(
        {
            "type": "spellcheck",
            "query": {"original": "helo"},
            "results": [{"query": "hello"}],
        }
    )

    assert response.results[0].query == "hello"


def test_summarizer_response_is_flexible_but_typed() -> None:
    response = SummarizerSearchApiResponse.model_validate(
        {
            "status": "complete",
            "title": "What is K2?",
            "summary": [
                {"type": "token", "data": "K2 is the second highest mountain."}
            ],
            "followups": ["How tall is K2?"],
            "entities_info": [{"name": "K2", "type": "Mountain"}],
        }
    )

    assert response.status == "complete"
    assert isinstance(response.summary, list)
    assert response.summary
    assert response.summary[0].data == "K2 is the second highest mountain."
    assert response.entities_info is not None
    assert response.entities_info
    assert response.entities_info[0].name == "K2"


def test_summarizer_query_requires_key() -> None:
    with pytest.raises(ValidationError):
        SummarizerQueryParams(key="")


def test_web_search_allows_numeric_video_views() -> None:
    response = WebSearchApiResponse.model_validate(
        {
            "type": "search",
            "videos": {
                "type": "videos",
                "results": [
                    {
                        "type": "video_result",
                        "title": "Python tutorial",
                        "url": "https://example.com/video",
                        "description": "Learn Python",
                        "video": {"views": 313095},
                    }
                ],
            },
        }
    )

    assert response.videos is not None
    assert response.videos.results[0].video.views == 313095


def test_news_search_allows_sparse_live_profiles() -> None:
    response = NewsSearchApiResponse.model_validate(
        {
            "type": "news",
            "query": {"original": "technology"},
            "results": [
                {
                    "type": "news_result",
                    "title": "Tech story",
                    "url": "https://example.com/news",
                    "description": "Latest technology coverage",
                    "age": "5 days ago",
                    "profile": {
                        "name": "NYTimes",
                        "url": "https://example.com/profile",
                    },
                }
            ],
        }
    )

    assert response.results[0].profile is not None
    assert response.results[0].profile.name == "NYTimes"
