from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal


class SuggestSearchQueryParams(BaseModel):
    q: str = Field(
        ...,
        min_length=1,
        max_length=400,
        description="The user’s suggest search query term, cannot be empty. Max length 400.",
    )
    country: Optional[str] = Field(
        default="US",
        min_length=2,
        max_length=2,
        description="2 character country code (e.g., 'US').",
    )
    lang: Optional[str] = Field(
        default="en",
        min_length=2,
        description="The language code, 2 or more characters (e.g., 'en').",
    )
    count: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="How many suggestions to return (1-20). Default is 5.",
    )
    rich: Optional[bool] = Field(
        default=False, description="Whether to enhance suggestions with rich results."
    )

    @field_validator("q")
    @classmethod
    def q_word_limit(cls, v: str) -> str:
        if len(v.split()) > 50:
            raise ValueError("The 'q' parameter must not exceed 50 words.")
        return v

    @field_validator("country")
    @classmethod
    def country_code_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) != 2:
            raise ValueError("Country codes must be exactly 2 characters.")
        return v

    @field_validator("lang")
    @classmethod
    def lang_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 2:
            raise ValueError("Language code must be at least 2 characters long.")
        return v


class Query(BaseModel):
    original: str = Field(..., description="The original query that was requested.")


class SuggestResult(BaseModel):
    query: str = Field(..., description="Suggested query completion.")
    is_entity: Optional[bool] = Field(
        None, description="Whether the suggested enriched query is an entity."
    )
    title: Optional[str] = Field(
        None, description="The suggested query enriched title."
    )
    description: Optional[str] = Field(
        None, description="The suggested query enriched description."
    )
    img: Optional[str] = Field(
        None, description="The suggested query enriched image URL."
    )


class SuggestSearchApiResponse(BaseModel):
    type: Literal["suggest"] = Field(
        ..., description="The type of search api result. The value is always `suggest`."
    )
    query: Query = Field(
        ...,
        description="Suggest search query string. Only the original query is returned.",
    )
    results: List[SuggestResult] = Field(
        ..., description="The list of suggestions for the given query."
    )

    @field_validator("type")
    @classmethod
    def type_must_be_suggest(cls, v: str) -> str:
        if v != "suggest":
            raise ValueError('type must be "suggest"')
        return v
