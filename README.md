# brave-api

[![Supported versions](https://img.shields.io/pypi/pyversions/that-depends.svg)](https://pypi.python.org/pypi/brave-api-client)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/brave-api-client?period=monthly&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=YELLOWGREEN&left_text=downloads%2Fmonth)](https://pepy.tech/projects/brave-api-client)
[![GitHub stars](https://img.shields.io/github/stars/xelandernt/brave-api)](https://github.com/xelandernt/brave-api/stargazers)

Typed Python client for the Brave Search API.

This package uses `niquests` for HTTP transport and `pydantic` models for
request validation and response parsing.

## Installation

```bash
uv add brave-api-client
```

Or with `pip`:

```bash
pip install brave-api-client
```

## Authentication

Pass your API key directly:

```python
from brave_api.client import Brave

client = Brave(api_key="your-api-key")
```

Or set `BRAVE_API_KEY`:

```bash
export BRAVE_API_KEY=your-api-key
```

## Available clients

- `Brave`: synchronous client
- `AsyncBrave`: asynchronous client

## Documentation

For Brave's official API docs and endpoint details, see:

- [Brave Search API documentation](https://api-dashboard.search.brave.com/documentation)
- [Brave Search API Spec](https://api-dashboard.search.brave.com/api-reference/web/search/get)

## Quick start

### Synchronous client

```python
from brave_api.client import Brave
from brave_api.web_search.models import WebSearchQueryParams

client = Brave(api_key="your-api-key")
response = client.web_search(WebSearchQueryParams(q="python web frameworks"))
data = response.parsed_data

if data.web:
    for result in data.web.results:
        print(result.title, result.url)
```

### Asynchronous client

```python
import asyncio

from brave_api.client import AsyncBrave
from brave_api.web_search.models import WebSearchQueryParams


async def main() -> None:
    client = AsyncBrave(api_key="your-api-key")
    response = await client.web_search(WebSearchQueryParams(q="privacy search"))
    data = response.parsed_data

    if data.web:
        for result in data.web.results:
            print(result.title)


asyncio.run(main())
```

## Responses API

All non-streaming methods return a `Response[Model]` wrapper, including methods
on `AsyncBrave`. Use `response.parsed_data` for the validated Pydantic model and
`response.raw_response` for the underlying `niquests` response.

`AsyncBrave.summarizer_summary_streaming()` returns
`AsyncResponse[SummarizerStreamingEvent]`, and
`Brave.summarizer_summary_streaming()` returns
`Response[SummarizerStreamingEvent]`. Consume streaming events with
`iter_lines_parsed()`.

## Retry configuration

Retries are opt-in. The default `Brave` and `AsyncBrave` clients do not retry
unless you pass a `RetryConfig`.

### Fixed-delay retries

```python
from brave_api.client import Brave
from brave_api.retries import FixedDelayRetryStrategy, RetryConfig

client = Brave(
    api_key="your-api-key",
    retry_config=RetryConfig(
        max_attempts=4,
        strategy=FixedDelayRetryStrategy(delay_seconds=1.0),
    ),
)
```

### Exponential backoff

```python
from brave_api.client import AsyncBrave
from brave_api.retries import ExponentialBackoffRetryStrategy, RetryConfig

client = AsyncBrave(
    api_key="your-api-key",
    retry_config=RetryConfig(
        max_attempts=5,
        strategy=ExponentialBackoffRetryStrategy(
            base_delay_seconds=0.5,
            max_delay_seconds=8.0,
        ),
    ),
)
```

### Retry-After aware retries

`RetryAfterRetryStrategy` uses the server's `Retry-After` header when present
and falls back to another strategy otherwise.

```python
from brave_api.client import Brave
from brave_api.retries import (
    ExponentialBackoffRetryStrategy,
    RetryAfterRetryStrategy,
    RetryConfig,
)

client = Brave(
    api_key="your-api-key",
    retry_config=RetryConfig(
        max_attempts=3,
        strategy=RetryAfterRetryStrategy(
            fallback_strategy=ExponentialBackoffRetryStrategy(
                base_delay_seconds=1.0,
                max_delay_seconds=10.0,
            )
        ),
    ),
)
```

By default, `RetryConfig` retries transient transport failures plus HTTP
`429`, `500`, `502`, `503`, and `504`.

## Supported APIs and methods

All methods below are available on both `Brave` and `AsyncBrave`. Async methods
use the same names and are awaited.

| API group                | Brave endpoint(s)                      | Client methods                   | Request model(s)                  | Return type                                                                                           |
|--------------------------|----------------------------------------|----------------------------------|-----------------------------------|-------------------------------------------------------------------------------------------------------|
| Web search               | `/res/v1/web/search`                   | `web_search()`                   | `WebSearchQueryParams`            | `Response[WebSearchApiResponse]`                                                                       |
| Rich search              | `/res/v1/web/rich`                     | `rich_search()`                  | `RichSearchQueryParams`           | `Response[RichSearchApiResponse]`                                                                      |
| Image search             | `/res/v1/images/search`                | `image_search()`                 | `ImageSearchAPIParams`            | `Response[ImageSearchApiResponse]`                                                                     |
| News search              | `/res/v1/news/search`                  | `news_search()`                  | `NewsSearchQueryParams`           | `Response[NewsSearchApiResponse]`                                                                      |
| Video search             | `/res/v1/videos/search`                | `video_search()`                 | `VideoSearchQueryParams`          | `Response[VideoSearchApiResponse]`                                                                     |
| Spellcheck               | `/res/v1/spellcheck/search`            | `spellcheck()`                   | `SpellcheckQueryParams`           | `Response[SpellcheckApiResponse]`                                                                      |
| Suggest                  | `/res/v1/suggest/search`               | `suggest()`                      | `SuggestSearchQueryParams`        | `Response[SuggestSearchApiResponse]`                                                                   |
| Place search             | `/res/v1/local/place_search`           | `place_search()`                 | `PlaceSearchQueryParams`          | `Response[PlaceSearchApiResponse]`                                                                     |
| Local points of interest | `/res/v1/local/pois`                   | `local_pois()`                   | `LocalSearchQueryParams`          | `Response[LocalPoiSearchApiResponse]`                                                                  |
| Local descriptions       | `/res/v1/local/descriptions`           | `local_descriptions()`           | `LocalDescriptionsQueryParams`    | `Response[LocalDescriptionsSearchApiResponse]`                                                         |
| LLM context              | `/res/v1/llm/context`                  | `llm_context()`                  | `LLMContextQueryParams`           | `Response[LLMContextApiResponse]`                                                                       |
| Answers                  | `/res/v1/chat/completions`             | `answers()`                      | `AnswersRequest`                  | `Response[AnswersApiResponse]`                                                                         |
| Answers streaming        | `/res/v1/chat/completions`             | `answers_streaming()`            | `AnswersRequest`                  | `Response[AnswersStreamingEvent]` on `Brave`; `AsyncResponse[AnswersStreamingEvent]` on `AsyncBrave` |
| Summarizer search        | `/res/v1/summarizer/search`            | `summarizer_search()`            | `SummarizerQueryParams`           | `Response[SummarizerSearchApiResponse]`                                                                |
| Summarizer summary       | `/res/v1/summarizer/summary`           | `summarizer_summary()`           | `SummarizerQueryParams`           | `Response[SummarizerSummaryApiResponse]`                                                               |
| Summarizer title         | `/res/v1/summarizer/title`             | `summarizer_title()`             | `SummarizerQueryParams`           | `Response[SummarizerTitleApiResponse]`                                                                 |
| Summarizer enrichments   | `/res/v1/summarizer/enrichments`       | `summarizer_enrichments()`       | `SummarizerQueryParams`           | `Response[SummarizerEnrichmentsApiResponse]`                                                           |
| Summarizer followups     | `/res/v1/summarizer/followups`         | `summarizer_followups()`         | `SummarizerQueryParams`           | `Response[SummarizerFollowupsApiResponse]`                                                             |
| Summarizer entity info   | `/res/v1/summarizer/entity_info`       | `summarizer_entity_info()`       | `SummarizerEntityInfoQueryParams` | `Response[SummarizerEntityInfoApiResponse]`                                                            |
| Summarizer streaming     | `/res/v1/summarizer/summary_streaming` | `summarizer_summary_streaming()` | `SummarizerQueryParams`           | `Response[SummarizerStreamingEvent]` on `Brave`; `AsyncResponse[SummarizerStreamingEvent]` on `AsyncBrave` |

## API overview

### Web search

The web search client is the main entry point for Brave Search. It returns a
typed response that can include web results and additional sections such as
news, videos, locations, discussions, infoboxes, and summarizer metadata.

### Image, news, and video search

These endpoints expose Brave's vertical-specific search APIs with typed request
and response models for media and content-focused workflows.

### Suggest and spellcheck

These APIs support search UX features such as autocomplete, typo correction,
and query refinement.

### Local APIs

The local APIs cover both discovery and enrichment for places and points of
interest. A common flow is to use `place_search()` to find locations, then
fetch follow-up POI details or descriptions with `local_pois()` and
`local_descriptions()`.

### LLM context and answers APIs

The package includes dedicated models for Brave's LLM grounding APIs.
`llm_context()` returns extracted grounding content for your own LLM workflows,
while `answers()` and `answers_streaming()` expose the OpenAI-compatible
chat-completions endpoint backed by Brave Search.

### Summarizer APIs

The package includes typed support for Brave's summarizer-related endpoints,
including summary retrieval, streaming output, enrichments, followups, titles,
and entity information.
