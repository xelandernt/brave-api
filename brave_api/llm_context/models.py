from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from brave_api.util import validate_freshness, validate_query_word_limit


class LLMContextQueryParams(BaseModel):
    """Query parameters for `/llm/context`."""

    q: str = Field(
        ...,
        min_length=1,
        max_length=400,
        description="The user’s search query term. Maximum 400 chars and 50 words.",
    )
    country: Optional[str] = Field(
        "US",
        min_length=2,
        max_length=2,
        description="2 character country code used to scope the search.",
    )
    search_lang: Optional[str] = Field(
        "en",
        min_length=2,
        description="2+ character language code for the result language.",
    )
    count: Optional[int] = Field(
        20,
        ge=1,
        le=50,
        description="Maximum number of search results to consider.",
    )
    maximum_number_of_urls: Optional[int] = Field(
        20,
        ge=1,
        le=50,
        description="Maximum number of URLs to include in the response.",
    )
    maximum_number_of_tokens: Optional[int] = Field(
        8192,
        ge=1024,
        le=32768,
        description="Approximate maximum number of tokens in the returned context.",
    )
    maximum_number_of_snippets: Optional[int] = Field(
        50,
        ge=1,
        le=100,
        description="Maximum number of snippets across all URLs.",
    )
    context_threshold_mode: Optional[str] = Field(
        "balanced",
        pattern="^(strict|balanced|lenient|disabled)$",
        description="Threshold mode used to filter content by relevance.",
    )
    maximum_number_of_tokens_per_url: Optional[int] = Field(
        4096,
        ge=512,
        le=8192,
        description="Maximum number of tokens to include per URL.",
    )
    maximum_number_of_snippets_per_url: Optional[int] = Field(
        50,
        ge=1,
        le=100,
        description="Maximum number of snippets to include per URL.",
    )
    goggles: Optional[str | list[str]] = Field(
        None,
        description="Goggle URL or inline definition used to rerank results.",
    )
    freshness: Optional[str] = Field(
        None,
        description=(
            "Limits discovery to a time window. One of: pd, pw, pm, py, or a "
            "date range in the form YYYY-MM-DDtoYYYY-MM-DD."
        ),
    )
    enable_local: Optional[bool] = Field(
        None,
        description="Whether to enable local recall.",
    )

    @field_validator("q")
    @classmethod
    def validate_q_word_limit(cls, value: str) -> str:
        return validate_query_word_limit(value)

    @field_validator("freshness")
    @classmethod
    def validate_freshness_value(cls, value: Optional[str]) -> Optional[str]:
        return validate_freshness(value)


class LLMContextGroundingItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    title: str
    snippets: list[str]


class LLMContextPlace(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    snippets: Optional[list[str]] = None


class LLMContextGrounding(BaseModel):
    model_config = ConfigDict(extra="allow")

    generic: list[LLMContextGroundingItem]
    poi: Optional[LLMContextPlace] = None
    map: Optional[list[LLMContextPlace]] = None


class LLMContextSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: Optional[str] = None
    hostname: Optional[str] = None
    age: Optional[list[str]] = None


class LLMContextApiResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    grounding: LLMContextGrounding
    sources: dict[str, LLMContextSource]
