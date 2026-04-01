from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from brave_api.util import validate_query_word_limit, validate_freshness
from brave_api.web_search.models import NewsResult, Query


class NewsSearchQueryParams(BaseModel):
    q: str = Field(..., min_length=1, max_length=400)
    search_lang: Optional[str] = Field("en", min_length=2)
    ui_lang: Optional[str] = Field("en-US")
    country: Optional[str] = Field("US", min_length=2, max_length=3)
    safesearch: Optional[Literal["off", "moderate", "strict"]] = Field("strict")
    count: Optional[int] = Field(20, ge=1, le=50)
    offset: Optional[int] = Field(0, ge=0, le=9)
    spellcheck: Optional[bool] = Field(True)
    freshness: Optional[str] = Field(None)
    goggles: Optional[List[str]] = Field(None)
    operators: Optional[bool] = Field(True)

    @field_validator("q")
    @classmethod
    def validate_q_word_limit(cls, v: str) -> str:
        return validate_query_word_limit(v)

    @field_validator("freshness")
    @classmethod
    def validate_freshness(cls, v: Optional[str]) -> Optional[str]:
        return validate_freshness(v)

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v and v != "ALL" and len(v) != 2:
            raise ValueError("Country code must be 2 characters or ALL")
        return v


class NewsSearchApiResponse(BaseModel):
    """Top-level typed response returned by `/news/search`."""

    type: Literal["news"]
    query: Query
    results: List[NewsResult]
