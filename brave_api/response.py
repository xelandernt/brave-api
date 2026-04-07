from collections.abc import AsyncIterator, Iterator
from typing import Generic, TypeVar

import niquests
from niquests.models import ITER_CHUNK_SIZE
from pydantic import BaseModel

DataType = TypeVar("DataType", bound=BaseModel)
ValueT = TypeVar("ValueT")


class Response(Generic[DataType]):
    __slots__ = ("_model", "_parsed_data", "_response")

    def __init__(
        self,
        response: niquests.Response,
        model: type[DataType],
    ):
        self._response = response
        self._model = model
        self._parsed_data: DataType | None = None

    @property
    def request(self) -> niquests.PreparedRequest | None:
        return self._response.request

    @property
    def raw_response(self) -> niquests.Response:
        return self._response

    @property
    def status_code(self) -> int | None:
        return self._response.status_code

    @property
    def ok(self) -> bool:
        return self._response.ok

    @property
    def is_redirect(self) -> bool:
        return self._response.is_redirect

    @property
    def is_error(self) -> bool:
        return self._response.is_error

    @property
    def content(self) -> bytes | None:
        return self._response.content

    @property
    def text(self) -> str | None:
        return self._response.text

    def json(self, **kwargs: object) -> object:
        return self._response.json(**kwargs)

    @property
    def parsed_data(self) -> DataType:
        if self._parsed_data is None:
            self._parsed_data = self._model.model_validate(self.json())
        return self._parsed_data

    def raise_for_status(self) -> None:
        self._response.raise_for_status()

    def iter_raw(self, chunk_size: int = ITER_CHUNK_SIZE) -> Iterator[bytes]:
        for v in self._response.iter_raw(chunk_size):
            yield v

    def iter_content(
        self, chunk_size: int = ITER_CHUNK_SIZE, decode_unicode: bool = False
    ) -> Iterator[bytes | str]:
        yield from self._response.iter_content(
            chunk_size, decode_unicode=decode_unicode
        )

    def iter_lines(
        self,
        chunk_size: int = ITER_CHUNK_SIZE,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> Iterator[bytes | str]:
        yield from self._response.iter_lines(
            chunk_size, decode_unicode=decode_unicode, delimiter=delimiter
        )


class AsyncResponse(Generic[DataType]):
    __slots__ = ("_model", "_parsed_data", "_response")

    def __init__(
        self,
        response: niquests.AsyncResponse,
        model: type[DataType],
    ):
        self._response = response
        self._model = model
        self._parsed_data: DataType | None = None

    @property
    def request(self) -> niquests.PreparedRequest | None:
        return self._response.request

    @property
    def raw_response(self) -> niquests.AsyncResponse:
        return self._response

    @property
    def status_code(self) -> int | None:
        return self._response.status_code

    @property
    def ok(self) -> bool:
        return self._response.ok

    @property
    def is_redirect(self) -> bool:
        return self._response.is_redirect

    @property
    def is_error(self) -> bool:
        return self._response.is_error

    @property
    async def content(self) -> bytes | None:
        return await self._response.content

    @property
    async def text(self) -> str | None:
        return await self._response.text

    async def json(self, **kwargs: object) -> object:
        return await self._response.json(**kwargs)

    @property
    async def parsed_data(self) -> DataType:
        if self._parsed_data is None:
            self._parsed_data = self._model.model_validate(await self.json())
        return self._parsed_data

    def raise_for_status(self) -> None:
        self._response.raise_for_status()

    async def iter_raw(self, chunk_size: int = ITER_CHUNK_SIZE) -> AsyncIterator[bytes]:
        async for v in await self._response.iter_raw(chunk_size):
            yield v

    async def iter_content(
        self, chunk_size: int = ITER_CHUNK_SIZE, decode_unicode: bool = False
    ) -> AsyncIterator[bytes | str]:
        async for value in await self._response.iter_content(
            chunk_size, decode_unicode=decode_unicode
        ):
            yield value

    async def iter_lines(
        self,
        chunk_size: int = ITER_CHUNK_SIZE,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> AsyncIterator[bytes | str]:
        async for value in await self._response.iter_lines(
            chunk_size, decode_unicode=decode_unicode, delimiter=delimiter
        ):
            yield value
