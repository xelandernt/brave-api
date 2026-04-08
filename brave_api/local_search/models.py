from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brave_api.util import validate_location_ids, validate_query_word_limit
from brave_api.web_search.models import LocationResult, Query


class LocationDescription(BaseModel):
    type: str = "local_description"
    id: str
    description: Optional[str] = None


class LocalPoiSearchApiResponse(BaseModel):
    type: str = "local_pois"
    results: Optional[list[LocationResult]] = None


class LocalDescriptionsSearchApiResponse(BaseModel):
    type: str = "local_descriptions"
    results: Optional[list[LocationDescription]] = None


class ResolvedLocation(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PlaceSearchApiResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "locations"
    query: Optional[Query] = None
    results: Optional[list[LocationResult]] = None
    location: Optional[ResolvedLocation] = None
    resolved_location: Optional[ResolvedLocation] = None


class LocalSearchQueryParams(BaseModel):
    """
    Validated query parameters for `/local/pois`.

    The `ids` values come from location entries returned by web search.
    """

    ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of 1 to 20 non-empty unique location IDs.",
    )
    search_lang: Optional[str] = Field(
        "en",
        min_length=2,
        description="2+ character language code. See language codes list.",
    )
    ui_lang: Optional[str] = Field(
        "en-US",
        description="Format <language_code>-<country_code> (see RFC9110 and UI language codes list).",
    )
    units: Optional[str] = Field(
        None,
        pattern="^(metric|imperial)$",
        description="Measurement units: metric, imperial.",
    )

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        return validate_location_ids(value)


class LocalDescriptionsQueryParams(BaseModel):
    """Validated query parameters for `/local/descriptions`."""

    ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of 1 to 20 non-empty unique location IDs.",
    )

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        return validate_location_ids(value)


class PlaceSearchQueryParams(BaseModel):
    """Validated query parameters for `/local/place_search`."""

    q: Optional[str] = Field(
        None,
        max_length=400,
        description=(
            "Query string to search for points of interest. Omit or pass an empty "
            "string to explore general places in the given area."
        ),
    )
    latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude of the geographical coordinates.",
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude of the geographical coordinates.",
    )
    location: Optional[str] = Field(
        None,
        min_length=1,
        description="Location string used instead of latitude and longitude.",
    )
    radius: Optional[int] = Field(
        None,
        ge=1,
        description="Search radius around the given coordinates, in meters.",
    )
    count: Optional[int] = Field(
        20,
        ge=1,
        le=50,
        description="Number of results to return (max 50).",
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
    ui_lang: Optional[str] = Field(
        "en-US",
        description="Preferred UI language in the response.",
    )
    units: Optional[str] = Field(
        "metric",
        pattern="^(metric|imperial)$",
        description="Measurement units: metric or imperial.",
    )
    safesearch: Optional[str] = Field(
        "strict",
        pattern="^(off|moderate|strict)$",
        description="Adult content filter: off, moderate, strict.",
    )
    spellcheck: Optional[bool] = Field(
        True,
        description="Whether to apply spellcheck before executing the search.",
    )
    geoloc: Optional[str] = Field(
        None,
        description="Optional geolocation token used to refine results.",
    )

    @field_validator("q")
    @classmethod
    def validate_q_word_limit(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return value
        return validate_query_word_limit(value)

    @model_validator(mode="after")
    def validate_area_parameters(self) -> PlaceSearchQueryParams:
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None

        if has_latitude != has_longitude:
            raise ValueError("latitude and longitude must be provided together")
        if not self.location and not has_latitude:
            raise ValueError(
                "Either location or both latitude and longitude are required"
            )
        return self
