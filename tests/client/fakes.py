from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Iterable, Iterator
from typing import TypedDict

import niquests

JsonObject = dict[str, object]
HeadersMap = dict[str, str]
ProxyConfig = dict[str, str]
QueryParamValue = str | list[str] | None
QueryParams = dict[str, QueryParamValue]


class RequestCall(TypedDict):
    method: str
    url: str
    headers: HeadersMap | None
    params: QueryParams | None
    json: JsonObject | None
    proxies: ProxyConfig | None
    stream: bool | None


def _encode_line(line: str | bytes) -> bytes:
    return line if isinstance(line, bytes) else line.encode()


def _decode_line(line: str | bytes) -> str:
    return line if isinstance(line, str) else line.decode()


class FakeResponse:
    request = None
    is_redirect = False

    def __init__(
        self,
        payload: JsonObject | None = None,
        lines: Iterable[str | bytes] | None = None,
        *,
        status_code: int = 200,
        headers: HeadersMap | None = None,
    ) -> None:
        self.payload = payload or {}
        self.lines = list(lines or [])
        self.status_code = status_code
        self.headers = headers or {}
        self.url = "https://example.com"
        self.ok = status_code < 400
        serialized_payload = json.dumps(self.payload) if self.payload else ""
        self.content = serialized_payload.encode() if serialized_payload else None
        self.text = serialized_payload or None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise niquests.exceptions.HTTPError(
                f"{self.status_code} error",
                response=self,
            )

    def json(self, **kwargs: object) -> JsonObject:
        del kwargs
        return self.payload

    def iter_raw(self, chunk_size: int = -1) -> Iterator[bytes]:
        del chunk_size
        for line in self.lines:
            yield _encode_line(line)

    def iter_content(
        self, chunk_size: int = -1, decode_unicode: bool = False
    ) -> Iterator[bytes | str]:
        del chunk_size
        for line in self.lines:
            yield _decode_line(line) if decode_unicode else _encode_line(line)

    def iter_lines(
        self,
        chunk_size: int = -1,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> Iterator[bytes | str]:
        del delimiter
        yield from self.iter_content(
            chunk_size=chunk_size,
            decode_unicode=decode_unicode,
        )


class FakeAsyncResponse:
    request = None
    is_redirect = False

    def __init__(
        self,
        payload: JsonObject | None = None,
        lines: Iterable[str | bytes] | None = None,
        *,
        status_code: int = 200,
        headers: HeadersMap | None = None,
    ) -> None:
        self.payload = payload or {}
        self.lines = list(lines or [])
        self.status_code = status_code
        self.headers = headers or {}
        self.url = "https://example.com"
        self.ok = status_code < 400
        serialized_payload = json.dumps(self.payload) if self.payload else ""
        self._content = serialized_payload.encode() if serialized_payload else None
        self._text = serialized_payload or None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise niquests.exceptions.HTTPError(
                f"{self.status_code} error",
                response=self,
            )

    @property
    def content(self) -> Awaitable[bytes | None]:
        return self._get_content()

    async def _get_content(self) -> bytes | None:
        return self._content

    @property
    def text(self) -> Awaitable[str | None]:
        return self._get_text()

    async def _get_text(self) -> str | None:
        return self._text

    async def json(self, **kwargs: object) -> JsonObject:
        del kwargs
        return self.payload

    async def iter_raw(self, chunk_size: int = -1) -> AsyncIterator[bytes]:
        del chunk_size
        for line in self.lines:
            yield _encode_line(line)

    async def iter_content(
        self, chunk_size: int = -1, decode_unicode: bool = False
    ) -> AsyncIterator[bytes | str]:
        del chunk_size
        for line in self.lines:
            yield _decode_line(line) if decode_unicode else _encode_line(line)

    async def iter_lines(
        self,
        chunk_size: int = -1,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> AsyncIterator[bytes | str]:
        del delimiter
        async for line in self.iter_content(
            chunk_size=chunk_size,
            decode_unicode=decode_unicode,
        ):
            yield line


class SyncGetStub:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[RequestCall] = []

    def __call__(
        self,
        url: str,
        *,
        params: QueryParams | None = None,
        headers: HeadersMap | None = None,
        proxies: ProxyConfig | None = None,
        stream: bool | None = None,
        **kwargs: object,
    ) -> FakeResponse:
        del kwargs
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "headers": headers,
                "params": params,
                "json": None,
                "proxies": proxies,
                "stream": stream,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        response.url = url
        return response


class AsyncGetStub:
    def __init__(
        self,
        responses: list[FakeResponse | FakeAsyncResponse | Exception],
    ) -> None:
        self.responses = responses
        self.calls: list[RequestCall] = []

    async def __call__(
        self,
        url: str,
        *,
        params: QueryParams | None = None,
        headers: HeadersMap | None = None,
        proxies: ProxyConfig | None = None,
        stream: bool | None = None,
        **kwargs: object,
    ) -> FakeResponse | FakeAsyncResponse:
        del kwargs
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "headers": headers,
                "params": params,
                "json": None,
                "proxies": proxies,
                "stream": stream,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if stream and isinstance(response, FakeResponse):
            raise TypeError("Streaming requests require FakeAsyncResponse")
        if not stream and isinstance(response, FakeAsyncResponse):
            raise TypeError("Non-streaming requests require FakeResponse")
        response.url = url
        return response


class SyncPostStub:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[RequestCall] = []

    def __call__(
        self,
        url: str,
        *,
        json: JsonObject | None = None,
        headers: HeadersMap | None = None,
        proxies: ProxyConfig | None = None,
        stream: bool | None = None,
        **kwargs: object,
    ) -> FakeResponse:
        del kwargs
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "headers": headers,
                "params": None,
                "json": json,
                "proxies": proxies,
                "stream": stream,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        response.url = url
        return response


class AsyncPostStub:
    def __init__(
        self,
        responses: list[FakeResponse | FakeAsyncResponse | Exception],
    ) -> None:
        self.responses = responses
        self.calls: list[RequestCall] = []

    async def __call__(
        self,
        url: str,
        *,
        json: JsonObject | None = None,
        headers: HeadersMap | None = None,
        proxies: ProxyConfig | None = None,
        stream: bool | None = None,
        **kwargs: object,
    ) -> FakeResponse | FakeAsyncResponse:
        del kwargs
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "headers": headers,
                "params": None,
                "json": json,
                "proxies": proxies,
                "stream": stream,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if stream and isinstance(response, FakeResponse):
            raise TypeError("Streaming requests require FakeAsyncResponse")
        if not stream and isinstance(response, FakeAsyncResponse):
            raise TypeError("Non-streaming requests require FakeResponse")
        response.url = url
        return response


def image_payload() -> JsonObject:
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


def news_payload() -> JsonObject:
    return {
        "type": "news",
        "query": {
            "original": "climate",
            "spellcheck_off": False,
            "show_strict_warning": False,
        },
        "results": [],
    }


def video_payload() -> JsonObject:
    return {
        "type": "videos",
        "query": {
            "original": "tutorial",
            "spellcheck_off": False,
            "show_strict_warning": False,
        },
        "results": [],
    }


def suggest_payload() -> JsonObject:
    return {
        "type": "suggest",
        "query": {"original": "pyth"},
        "results": [{"query": "python"}],
    }
