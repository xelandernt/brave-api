from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from brave_api.web_search.models import MetaUrl, Thumbnail


class ImageSearchAPIParams(BaseModel):
    q: str = Field(
        ...,
        min_length=1,
        max_length=400,
        description="The user's search query term. Maximum of 400 characters and 50 words.",
    )
    country: Optional[str] = Field(
        "US",
        min_length=2,
        max_length=3,
        description="2 character country code or ALL for worldwide results.",
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
        le=200,
        description="Number of results returned, defaults to 50, max 200.",
    )
    safesearch: Optional[Literal["off", "strict"]] = Field(
        "strict",
        description="Filters search results for adult content ('off', 'strict').",
    )
    spellcheck: Optional[bool] = Field(
        True, description="Whether to spellcheck the provided query."
    )

    @field_validator("q")
    @classmethod
    def q_max_words(cls, v: str) -> str:
        if len(v.split()) > 50:
            raise ValueError("Query cannot have more than 50 words")
        return v

    @field_validator("country")
    @classmethod
    def country_code_length(cls, v: Optional[str]) -> Optional[str]:
        if v and v != "ALL" and len(v) != 2:
            raise ValueError("Country code must be 2 characters or ALL")
        return v


class ImageProperties(BaseModel):
    url: str
    placeholder: str
    height: Optional[int] = None
    width: Optional[int] = None


class ImageSearchQuery(BaseModel):
    original: str
    altered: Optional[str] = None
    spellcheck_off: bool
    show_strict_warning: bool = False


class ImageResult(BaseModel):
    type: Literal["image_result"] = "image_result"
    title: str
    url: str
    source: str
    page_fetched: str
    thumbnail: Thumbnail
    properties: ImageProperties
    meta_url: MetaUrl


class ImageSearchApiResponse(BaseModel):
    """Top-level typed response returned by `/images/search`."""

    type: Literal["images"]
    query: ImageSearchQuery
    results: list[ImageResult]
