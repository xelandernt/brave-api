from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from brave_api.web_search.models import Thumbnail


class SummarizerQueryParams(BaseModel):
    """Shared query parameters for Brave summarizer endpoints."""

    key: str = Field(..., min_length=1)
    inline_references: Optional[bool] = Field(None)
    entity_info: Optional[bool] = Field(None)


class SummarizerEntityInfoQueryParams(BaseModel):
    """Query parameters for `/summarizer/entity_info`."""

    key: str = Field(..., min_length=1)
    entity: Optional[str] = Field(None)


class SummarizerToken(BaseModel):
    """A typed summary token block."""

    model_config = ConfigDict(extra="allow")

    type: Optional[str] = None
    data: Optional[Any] = None


class SummarizerReference(BaseModel):
    """A source reference attached to summary output."""

    model_config = ConfigDict(extra="allow")

    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    index: Optional[int] = None


class SummarizerImage(BaseModel):
    """An enrichment image returned by Brave summarizer."""

    model_config = ConfigDict(extra="allow")

    url: Optional[str] = None
    src: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[Thumbnail] = None


class SummarizerQAPair(BaseModel):
    """A question/answer enrichment pair."""

    model_config = ConfigDict(extra="allow")

    question: Optional[str] = None
    answer: Optional[str] = None


class SummarizerEntity(BaseModel):
    """Entity metadata returned by Brave summarizer."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    type: Optional[str] = None
    wikidata_id: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[Thumbnail] = None


class SummarizerEnrichments(BaseModel):
    """Additional summarizer enrichments such as images and references."""

    model_config = ConfigDict(extra="allow")

    raw_summary: Optional[str] = None
    images: Optional[List[SummarizerImage]] = None
    qa_pairs: Optional[List[SummarizerQAPair]] = None
    entity_details: Optional[List[SummarizerEntity]] = None
    references: Optional[List[SummarizerReference]] = None


class SummarizerFollowup(BaseModel):
    """A follow-up suggestion returned by Brave summarizer."""

    model_config = ConfigDict(extra="allow")

    question: Optional[str] = None
    key: Optional[str] = None


class SummarizerBaseResponse(BaseModel):
    """
    Flexible base response for Brave summarizer endpoints.

    The summarizer docs describe a shared set of fields including `status`,
    `title`, `summary`, `enrichments`, `followups`, and `entities_info`.
    """

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    title: Optional[str] = None
    key: Optional[str] = None
    summary: Optional[Union[str, List[SummarizerToken]]] = None
    enrichments: Optional[SummarizerEnrichments] = None
    followups: Optional[List[Union[str, SummarizerFollowup]]] = None
    entities_info: Optional[List[SummarizerEntity]] = None
    references: Optional[List[SummarizerReference]] = None


class SummarizerSearchApiResponse(SummarizerBaseResponse):
    """Typed response returned by `/summarizer/search`."""


class SummarizerSummaryApiResponse(SummarizerBaseResponse):
    """Typed response returned by `/summarizer/summary`."""


class SummarizerTitleApiResponse(BaseModel):
    """Typed response returned by `/summarizer/title`."""

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    key: Optional[str] = None
    title: Optional[str] = None


class SummarizerEnrichmentsApiResponse(BaseModel):
    """Typed response returned by `/summarizer/enrichments`."""

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    key: Optional[str] = None
    enrichments: Optional[SummarizerEnrichments] = None


class SummarizerFollowupsApiResponse(BaseModel):
    """Typed response returned by `/summarizer/followups`."""

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    key: Optional[str] = None
    followups: Optional[List[Union[str, SummarizerFollowup]]] = None


class SummarizerEntityInfoApiResponse(BaseModel):
    """Typed response returned by `/summarizer/entity_info`."""

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    key: Optional[str] = None
    entities_info: Optional[List[SummarizerEntity]] = None
    entity: Optional[SummarizerEntity] = None


class SummarizerStreamingEvent(BaseModel):
    """A single parsed line from the summarizer streaming endpoint."""

    raw: str
    event: Optional[str] = None
    text: Optional[str] = None
    payload_json: Optional[Dict[str, Any]] = None
