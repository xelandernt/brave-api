from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ImageSearchAPIParams(BaseModel):
    q: str = Field(
        ...,
        min_length=1,
        max_length=400,
        description="The user’s search query term. Maximum of 400 characters.",
    )
    country: Optional[str] = Field(
        "US",
        min_length=2,
        max_length=2,
        description="2 character country code, defaults to 'US'.",
    )
    search_lang: Optional[str] = Field(
        "en",
        min_length=2,
        max_length=10,
        description="Language code, defaults to 'en'.",
    )
    count: Optional[int] = Field(
        50,
        ge=1,
        le=100,
        description="Number of results returned, defaults to 50, max 100",
    )
    safesearch: Optional[Literal["off", "strict"]] = Field(
        "strict",
        description="Filters search results for adult content ('off', 'strict'). Default is 'strict'.",
    )
    spellcheck: Optional[bool] = Field(
        True, description="Whether to spellcheck provided query. Default true."
    )

    @field_validator("q")
    @classmethod
    def q_max_words(cls, v: str) -> str:
        if len(v.split()) > 50:
            raise ValueError("Query cannot have more than 50 words")
        return v

    @field_validator("country")
    @classmethod
    def country_two_chars(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) != 2:
            raise ValueError("Country code must be 2 characters")
        return v
