import niquests
import pytest
from pydantic import ValidationError

from brave_api.answers.models import AnswersApiResponse, AnswersRequest
from brave_api.client import AsyncBrave, Brave
from brave_api.image_search.models import ImageSearchAPIParams
from brave_api.llm_context.models import LLMContextApiResponse, LLMContextQueryParams
from brave_api.local_search.models import (
    LocalDescriptionsQueryParams,
    LocalSearchQueryParams,
    PlaceSearchQueryParams,
)
from brave_api.news_search.models import NewsSearchApiResponse, NewsSearchQueryParams
from brave_api.rich_search.models import RichSearchQueryParams
from brave_api.spellcheck.models import SpellcheckApiResponse, SpellcheckQueryParams
from brave_api.suggest.models import SuggestSearchQueryParams
from brave_api.summarizer_search.models import (
    SummarizerEntityInfoQueryParams,
    SummarizerQueryParams,
    SummarizerSearchApiResponse,
)
from brave_api.video_search.models import VideoSearchQueryParams
from brave_api.web_search.models import WebSearchApiResponse, WebSearchQueryParams
from tests.client.fakes import (
    AsyncGetStub,
    AsyncPostStub,
    FakeAsyncResponse,
    FakeResponse,
    SyncGetStub,
    SyncPostStub,
    image_payload,
    news_payload,
    suggest_payload,
    video_payload,
)


class StreamingErrorResponse(FakeResponse):
    def __init__(self, payload: dict[str, object], *, status_code: int) -> None:
        super().__init__(payload, status_code=status_code)
        self._content_loaded = False

    def __getattribute__(self, name: str) -> object:
        if name == "content":
            object.__setattr__(self, "_content_loaded", True)
        return super().__getattribute__(name)

    def json(self, **kwargs: object) -> dict[str, object]:
        if not self._content_loaded:
            raise AssertionError("streaming error content was not buffered")
        return super().json(**kwargs)


class AsyncStreamingErrorResponse(FakeAsyncResponse):
    def __init__(self, payload: dict[str, object], *, status_code: int) -> None:
        super().__init__(payload, status_code=status_code)
        self._content_loaded = False

    @property
    def content(self):  # type: ignore[override]
        return self._get_content()

    async def _get_content(self) -> bytes | None:
        self._content_loaded = True
        return await super()._get_content()

    async def json(self, **kwargs: object) -> dict[str, object]:
        if not self._content_loaded:
            raise AssertionError("streaming error content was not buffered")
        return await super().json(**kwargs)


def test_sync_client_methods_use_expected_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    get = SyncGetStub(
        [
            FakeResponse({"type": "search"}),
            FakeResponse(
                {
                    "type": "rich",
                    "results": [{"type": "weather", "title": "Weather"}],
                    "response_callback_info": {
                        "vertical": "weather",
                        "callback_key": "cb",
                    },
                }
            ),
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
            FakeResponse(
                {
                    "type": "locations",
                    "query": {"original": "coffee"},
                    "results": [],
                    "resolved_location": {"name": "San Francisco, CA, United States"},
                }
            ),
            FakeResponse({"type": "local_pois", "results": []}),
            FakeResponse({"type": "local_descriptions", "results": []}),
            FakeResponse(
                {
                    "grounding": {
                        "generic": [
                            {
                                "url": "https://example.com/python",
                                "title": "Example Python",
                                "snippets": ["Python is a programming language."],
                            }
                        ]
                    },
                    "sources": {
                        "https://example.com/python": {
                            "title": "Example Python",
                            "hostname": "example.com",
                            "age": [
                                "Monday, January 15, 2024",
                                "2024-01-15",
                                "380 days ago",
                            ],
                        }
                    },
                }
            ),
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
    post = SyncPostStub(
        [
            FakeResponse(
                {
                    "id": "chatcmpl-1",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "brave",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "Paris is fun"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 3,
                        "total_tokens": 13,
                    },
                }
            ),
            FakeResponse(
                lines=[
                    'data: {"choices":[{"delta":{"content":"stream chunk"}}]}',
                    "data: [DONE]",
                ]
            ),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    monkeypatch.setattr(session, "post", post)
    client = Brave(
        api_key="token",
        api_version="2023-01-01",
        client=session,
        proxy="http://proxy",
    )

    assert (
        client.web_search(WebSearchQueryParams(q="python")).parsed_data.type == "search"
    )
    rich_response = client.rich_search(
        RichSearchQueryParams(callback_key="cb")
    ).parsed_data
    assert rich_response.type == "rich"
    assert rich_response.response_callback_info is not None
    assert rich_response.response_callback_info.vertical == "weather"
    assert (
        client.image_search(ImageSearchAPIParams(q="cat")).parsed_data.type == "images"
    )
    assert (
        client.news_search(NewsSearchQueryParams(q="climate")).parsed_data.type
        == "news"
    )
    assert (
        client.video_search(VideoSearchQueryParams(q="tutorial")).parsed_data.type
        == "videos"
    )
    assert (
        client.spellcheck(SpellcheckQueryParams(q="helo")).parsed_data.type
        == "spellcheck"
    )
    assert (
        client.suggest(SuggestSearchQueryParams(q="pyth")).parsed_data.type == "suggest"
    )
    place_response = client.place_search(
        PlaceSearchQueryParams(q="coffee", location="san francisco united states")
    ).parsed_data
    assert place_response.type == "locations"
    assert place_response.resolved_location is not None
    assert place_response.resolved_location.name == "San Francisco, CA, United States"
    assert client.local_pois(
        LocalSearchQueryParams(ids=["loc-1"])
    ).parsed_data.type == ("local_pois")
    assert (
        client.local_descriptions(
            LocalDescriptionsQueryParams(ids=["loc-1"])
        ).parsed_data.type
        == "local_descriptions"
    )
    llm_context_response = client.llm_context(
        LLMContextQueryParams(q="python")
    ).parsed_data
    assert llm_context_response.grounding.generic[0].title == "Example Python"
    answers_response = client.answers(
        AnswersRequest(
            messages=[{"role": "user", "content": "best things to do in paris"}]
        )
    ).parsed_data
    assert answers_response.choices[0].message is not None
    assert answers_response.choices[0].message.content == "Paris is fun"
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
    answer_stream = list(
        client.answers_streaming(
            AnswersRequest(messages=[{"role": "user", "content": "stream"}])
        ).iter_lines_parsed()
    )
    assert answer_stream[0].text == "stream chunk"
    assert answer_stream[1].done is True
    summary_stream = list(
        client.summarizer_summary_streaming(
            SummarizerQueryParams(key="k")
        ).iter_lines_parsed()
    )
    assert summary_stream[0].event == "message"
    assert summary_stream[1].text == "chunk"

    assert [call["url"] for call in get.calls] == [
        "https://api.search.brave.com/res/v1/web/search",
        "https://api.search.brave.com/res/v1/web/rich",
        "https://api.search.brave.com/res/v1/images/search",
        "https://api.search.brave.com/res/v1/news/search",
        "https://api.search.brave.com/res/v1/videos/search",
        "https://api.search.brave.com/res/v1/spellcheck/search",
        "https://api.search.brave.com/res/v1/suggest/search",
        "https://api.search.brave.com/res/v1/local/place_search",
        "https://api.search.brave.com/res/v1/local/pois",
        "https://api.search.brave.com/res/v1/local/descriptions",
        "https://api.search.brave.com/res/v1/llm/context",
        "https://api.search.brave.com/res/v1/summarizer/search",
        "https://api.search.brave.com/res/v1/summarizer/summary",
        "https://api.search.brave.com/res/v1/summarizer/title",
        "https://api.search.brave.com/res/v1/summarizer/enrichments",
        "https://api.search.brave.com/res/v1/summarizer/followups",
        "https://api.search.brave.com/res/v1/summarizer/entity_info",
        "https://api.search.brave.com/res/v1/summarizer/summary_streaming",
    ]
    assert [call["url"] for call in post.calls] == [
        "https://api.search.brave.com/res/v1/chat/completions",
        "https://api.search.brave.com/res/v1/chat/completions",
    ]
    assert all(
        call["headers"] is not None
        and call["headers"]["X-Subscription-Token"] == "token"
        for call in [*get.calls, *post.calls]
    )
    assert all(
        call["headers"] is not None and call["headers"]["Api-Version"] == "2023-01-01"
        for call in [*get.calls, *post.calls]
    )
    assert all(
        call["proxies"] == {"http": "http://proxy", "https": "http://proxy"}
        for call in [*get.calls, *post.calls]
    )
    assert post.calls[0]["json"] is not None
    assert post.calls[0]["json"]["stream"] is False
    assert post.calls[1]["json"] is not None
    assert post.calls[1]["json"]["stream"] is True
    assert get.calls[-1]["stream"] is True
    assert post.calls[-1]["stream"] is True


async def test_async_client_methods_and_streaming_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    get = AsyncGetStub(
        [
            FakeResponse({"type": "search"}),
            FakeResponse(
                {
                    "grounding": {
                        "generic": [
                            {
                                "url": "https://example.com/async",
                                "title": "Async Example",
                                "snippets": ["Async context"],
                            }
                        ]
                    },
                    "sources": {
                        "https://example.com/async": {
                            "title": "Async Example",
                            "hostname": "example.com",
                        }
                    },
                }
            ),
            FakeAsyncResponse(lines=['data: {"text":"async chunk"}']),
        ]
    )
    post = AsyncPostStub(
        [
            FakeResponse(
                {
                    "id": "chatcmpl-async",
                    "object": "chat.completion",
                    "created": 2,
                    "model": "brave",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "async answer"},
                            "finish_reason": "stop",
                        }
                    ],
                }
            ),
            FakeAsyncResponse(
                lines=['data: {"choices":[{"delta":{"content":"async answer chunk"}}]}']
            ),
        ]
    )
    monkeypatch.setattr(session, "get", get)
    monkeypatch.setattr(session, "post", post)
    client = AsyncBrave(api_key="token", api_version="2023-01-01", client=session)

    web_response = await client.web_search(WebSearchQueryParams(q="python"))
    llm_response = await client.llm_context(LLMContextQueryParams(q="python"))
    answers_response = await client.answers(
        AnswersRequest(messages=[{"role": "user", "content": "hello"}])
    )
    answer_stream_response = await client.answers_streaming(
        AnswersRequest(messages=[{"role": "user", "content": "hello"}])
    )
    answer_stream = [
        event async for event in answer_stream_response.iter_lines_parsed()
    ]
    summary_stream_response = await client.summarizer_summary_streaming(
        SummarizerQueryParams(key="k")
    )
    summary_stream = [
        event async for event in summary_stream_response.iter_lines_parsed()
    ]
    answers_data = answers_response.parsed_data

    assert web_response.parsed_data.type == "search"
    assert llm_response.parsed_data.grounding.generic[0].title == "Async Example"
    assert answers_data.choices[0].message is not None
    assert answers_data.choices[0].message.content == "async answer"
    assert answer_stream[0].text == "async answer chunk"
    assert summary_stream[0].text == "async chunk"
    assert get.calls[0]["url"] == "https://api.search.brave.com/res/v1/web/search"
    assert get.calls[2]["stream"] is True
    assert (
        post.calls[0]["url"] == "https://api.search.brave.com/res/v1/chat/completions"
    )
    assert post.calls[1]["stream"] is True
    assert get.calls[0]["headers"] is not None
    assert get.calls[0]["headers"]["Api-Version"] == "2023-01-01"
    assert post.calls[0]["headers"] is not None
    assert post.calls[0]["headers"]["Api-Version"] == "2023-01-01"


def test_sync_streaming_http_error_keeps_response_body_readable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.Session()
    post = SyncPostStub(
        [
            StreamingErrorResponse(
                {
                    "error": {
                        "code": "OPTION_NOT_IN_PLAN",
                    }
                },
                status_code=400,
            )
        ]
    )
    monkeypatch.setattr(session, "post", post)
    client = Brave(api_key="token", client=session)

    with pytest.raises(niquests.exceptions.HTTPError) as error_info:
        client.answers_streaming(
            AnswersRequest(messages=[{"role": "user", "content": "hello"}])
        )

    assert error_info.value.response is not None
    assert error_info.value.response.json()["error"]["code"] == "OPTION_NOT_IN_PLAN"


async def test_async_streaming_http_error_keeps_response_body_readable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = niquests.AsyncSession()
    post = AsyncPostStub(
        [
            AsyncStreamingErrorResponse(
                {
                    "error": {
                        "code": "OPTION_NOT_IN_PLAN",
                    }
                },
                status_code=400,
            )
        ]
    )
    monkeypatch.setattr(session, "post", post)
    client = AsyncBrave(api_key="token", client=session)

    with pytest.raises(niquests.exceptions.HTTPError) as error_info:
        await client.answers_streaming(
            AnswersRequest(messages=[{"role": "user", "content": "hello"}])
        )

    assert error_info.value.response is not None
    payload = error_info.value.response.json()
    if hasattr(payload, "__await__"):
        payload = await payload
    assert payload["error"]["code"] == "OPTION_NOT_IN_PLAN"


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


def test_answers_response_is_openai_compatible_but_flexible() -> None:
    response = AnswersApiResponse.model_validate(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1,
            "model": "brave",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "K2 is the second highest mountain.",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
    )

    assert response.choices[0].message is not None
    assert response.choices[0].message.content == "K2 is the second highest mountain."


def test_llm_context_response_is_typed_but_extensible() -> None:
    response = LLMContextApiResponse.model_validate(
        {
            "grounding": {
                "generic": [
                    {
                        "url": "https://example.com/k2",
                        "title": "K2",
                        "snippets": ["K2 is the second highest mountain."],
                    }
                ],
                "poi": {
                    "name": "K2 Base Camp",
                    "snippets": ["Popular trekking destination."],
                },
            },
            "sources": {
                "https://example.com/k2": {
                    "title": "K2",
                    "hostname": "example.com",
                    "age": ["Monday, January 15, 2024", "2024-01-15", "380 days ago"],
                }
            },
        }
    )

    assert response.grounding.generic[0].title == "K2"
    assert response.sources["https://example.com/k2"].hostname == "example.com"


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
