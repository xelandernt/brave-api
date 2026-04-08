from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RichResponseCallbackInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    vertical: Optional[str] = None
    callback_key: Optional[str] = None
    callback_status: Optional[str] = None
    search_lang: Optional[str] = None


class RichSearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class RichSearchApiResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "rich"
    results: Optional[list[RichSearchResult]] = None
    response_callback_info: Optional[RichResponseCallbackInfo] = None


class RichSearchQueryParams(BaseModel):
    """Validated query parameters for `/web/rich`."""

    callback_key: str = Field(
        ...,
        min_length=1,
        description="Callback key returned by web search rich hints.",
    )
