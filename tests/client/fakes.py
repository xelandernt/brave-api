from typing import Any, AsyncIterator, Iterable


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        lines: Iterable[str | bytes] | None = None,
    ):
        self.payload = payload or {}
        self.lines = list(lines or [])

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload

    def iter_lines(
        self,
        chunk_size: int = -1,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> Iterable[str | bytes]:
        del chunk_size, decode_unicode, delimiter
        return iter(self.lines)


class FakeAsyncResponse:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        lines: Iterable[str | bytes] | None = None,
    ):
        self.payload = payload or {}
        self.lines = list(lines or [])

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload

    async def iter_lines(
        self,
        chunk_size: int = -1,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> AsyncIterator[str | bytes]:
        del chunk_size, decode_unicode, delimiter
        for line in self.lines:
            yield line


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


class FakeAsyncSession:
    def __init__(self, responses: list[FakeAsyncResponse]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> FakeAsyncResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def image_payload() -> dict[str, Any]:
    return {
        "type": "images",
        "query": {
            "original": "cat",
            "spellcheck_off": False,
            "show_strict_warning": False,
        },
        "results": [
            {
                "type": "image_result",
                "title": "Cat",
                "url": "https://example.com/page",
                "source": "example.com",
                "page_fetched": "2024-01-01T00:00:00Z",
                "thumbnail": {"src": "https://example.com/thumb.jpg"},
                "properties": {
                    "url": "https://example.com/image.jpg",
                    "placeholder": "https://example.com/placeholder.jpg",
                },
                "meta_url": {
                    "scheme": "https",
                    "netloc": "example.com",
                    "hostname": "example.com",
                    "favicon": "https://example.com/favicon.ico",
                    "path": "/page",
                },
            }
        ],
    }


def news_payload() -> dict[str, Any]:
    return {
        "type": "news",
        "query": {
            "original": "climate",
            "spellcheck_off": False,
            "show_strict_warning": False,
        },
        "results": [],
    }


def video_payload() -> dict[str, Any]:
    return {
        "type": "videos",
        "query": {
            "original": "tutorial",
            "spellcheck_off": False,
            "show_strict_warning": False,
        },
        "results": [],
    }


def spellcheck_payload() -> dict[str, Any]:
    return {
        "type": "spellcheck",
        "query": {"original": "helo"},
        "results": [{"query": "hello"}],
    }


def suggest_payload() -> dict[str, Any]:
    return {
        "type": "suggest",
        "query": {"original": "pyth"},
        "results": [{"query": "python"}],
    }
