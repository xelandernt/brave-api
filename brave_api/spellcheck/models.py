from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from brave_api.web_search.models import _validate_query_word_limit


class SpellcheckQueryParams(BaseModel):
    q: str = Field(..., min_length=1, max_length=400)
    lang: Optional[str] = Field("en", min_length=2)
    country: Optional[str] = Field("US", min_length=2, max_length=2)

    @field_validator("q")
    @classmethod
    def validate_q_word_limit(cls, v: str) -> str:
        return _validate_query_word_limit(v)


class SpellcheckQuery(BaseModel):
    """Original spellcheck query metadata."""

    original: str


class SpellcheckResult(BaseModel):
    """A corrected spellcheck suggestion."""

    query: str


class SpellcheckApiResponse(BaseModel):
    """Top-level typed response returned by `/spellcheck/search`."""

    type: Literal["spellcheck"]
    query: SpellcheckQuery
    results: List[SpellcheckResult]
