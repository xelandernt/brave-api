# brave-api


[![MyPy Strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/en/stable/getting_started.html#strict-mode-and-configuration)
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
response = client.search(WebSearchQueryParams(q="python web frameworks"))

if response.web:
    for result in response.web.results:
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

    if response.web:
        for result in response.web.results:
            print(result.title)


asyncio.run(main())
```

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

All methods below are available on both `BraveAPIClient` and
`AsyncBraveAPIClient`. Async methods use the same names and are awaited.

| API group                | Brave endpoint(s)                      | Client methods                   | Request model(s)                  | Response model(s)                                                                |
|--------------------------|----------------------------------------|----------------------------------|-----------------------------------|----------------------------------------------------------------------------------|
| Web search               | `/res/v1/web/search`                   | `search()`, `web_search()`       | `WebSearchQueryParams`            | `WebSearchApiResponse`                                                           |
| Image search             | `/res/v1/images/search`                | `image_search()`, `images()`     | `ImageSearchAPIParams`            | `ImageSearchApiResponse`                                                         |
| News search              | `/res/v1/news/search`                  | `news_search()`, `news()`        | `NewsSearchQueryParams`           | `NewsSearchApiResponse`                                                          |
| Video search             | `/res/v1/videos/search`                | `video_search()`, `videos()`     | `VideoSearchQueryParams`          | `VideoSearchApiResponse`                                                         |
| Spellcheck               | `/res/v1/spellcheck/search`            | `spellcheck()`                   | `SpellcheckQueryParams`           | `SpellcheckApiResponse`                                                          |
| Suggest                  | `/res/v1/suggest/search`               | `suggest()`, `suggest_search()`  | `SuggestSearchQueryParams`        | `SuggestSearchApiResponse`                                                       |
| Local points of interest | `/res/v1/local/pois`                   | `local_pois()`                   | `LocalSearchQueryParams`          | `LocalPoiSearchApiResponse`                                                      |
| Local descriptions       | `/res/v1/local/descriptions`           | `local_descriptions()`           | `LocalDescriptionsQueryParams`    | `LocalDescriptionsSearchApiResponse`                                             |
| Summarizer search        | `/res/v1/summarizer/search`            | `summarizer_search()`            | `SummarizerQueryParams`           | `SummarizerSearchApiResponse`                                                    |
| Summarizer summary       | `/res/v1/summarizer/summary`           | `summarizer_summary()`           | `SummarizerQueryParams`           | `SummarizerSummaryApiResponse`                                                   |
| Summarizer title         | `/res/v1/summarizer/title`             | `summarizer_title()`             | `SummarizerQueryParams`           | `SummarizerTitleApiResponse`                                                     |
| Summarizer enrichments   | `/res/v1/summarizer/enrichments`       | `summarizer_enrichments()`       | `SummarizerQueryParams`           | `SummarizerEnrichmentsApiResponse`                                               |
| Summarizer followups     | `/res/v1/summarizer/followups`         | `summarizer_followups()`         | `SummarizerQueryParams`           | `SummarizerFollowupsApiResponse`                                                 |
| Summarizer entity info   | `/res/v1/summarizer/entity_info`       | `summarizer_entity_info()`       | `SummarizerEntityInfoQueryParams` | `SummarizerEntityInfoApiResponse`                                                |
| Summarizer streaming     | `/res/v1/summarizer/summary_streaming` | `summarizer_summary_streaming()` | `SummarizerQueryParams`           | `Iterator[SummarizerStreamingEvent]` / `AsyncIterator[SummarizerStreamingEvent]` |

Aliases:

- `search()` is an alias for `web_search()`
- `images()` is an alias for `image_search()`
- `news()` is an alias for `news_search()`
- `videos()` is an alias for `video_search()`
- `suggest_search()` is an alias for `suggest()`

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

The local APIs provide enrichment for places and points of interest. A common
flow is to discover location IDs from search results and then fetch POI details
or descriptions.

### Summarizer APIs

The package includes typed support for Brave's summarizer-related endpoints,
including summary retrieval, streaming output, enrichments, followups, titles,
and entity information.
