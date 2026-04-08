from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnswersWebSearchOptions(BaseModel):
    """Optional search controls used by the answers API."""

    model_config = ConfigDict(extra="allow")

    country: Optional[str] = Field(None, min_length=2, max_length=2)
    language: Optional[str] = Field(None, min_length=2)
    safesearch: Optional[str] = Field(None, pattern="^(off|moderate|strict)$")
    enable_entities: Optional[bool] = Field(None)
    enable_citations: Optional[bool] = Field(None)
    enable_research: Optional[bool] = Field(None)
    research_allow_thinking: Optional[bool] = Field(None)
    research_maximum_number_of_tokens_per_query: Optional[int] = Field(None, ge=1)
    research_maximum_number_of_queries: Optional[int] = Field(None, ge=1)
    research_maximum_number_of_iterations: Optional[int] = Field(None, ge=1)
    research_maximum_number_of_seconds: Optional[int] = Field(None, ge=1)
    research_maximum_number_of_results_per_query: Optional[int] = Field(None, ge=1)


class AnswersInputMessage(BaseModel):
    """A single chat message sent to the answers API."""

    model_config = ConfigDict(extra="allow")

    role: str = Field(..., min_length=1)
    content: str | list[dict[str, object]]


class AnswersRequest(AnswersWebSearchOptions):
    """Request body for `/chat/completions`."""

    model_config = ConfigDict(extra="allow")

    messages: list[AnswersInputMessage] = Field(..., min_length=1)
    model: Optional[Literal["brave", "brave-pro"]] = None
    max_completion_tokens: Optional[int] = Field(None, ge=1)
    metadata: Optional[dict[str, object]] = None
    seed: Optional[int] = None
    stream: Optional[bool] = None
    web_search_options: Optional[AnswersWebSearchOptions] = None


class AnswersOutputMessage(BaseModel):
    """A chat completion message returned by the answers API."""

    model_config = ConfigDict(extra="allow")

    role: Optional[str] = None
    content: Optional[str | list[dict[str, object]]] = None


class AnswersDelta(BaseModel):
    """A streamed delta chunk returned by the answers API."""

    model_config = ConfigDict(extra="allow")

    role: Optional[str] = None
    content: Optional[str | list[dict[str, object]]] = None


class AnswersChoice(BaseModel):
    """A single completion choice returned by the answers API."""

    model_config = ConfigDict(extra="allow")

    index: Optional[int] = None
    message: Optional[AnswersOutputMessage] = None
    delta: Optional[AnswersDelta] = None
    finish_reason: Optional[str] = None


class AnswersUsage(BaseModel):
    """Token usage metadata returned by the answers API."""

    model_config = ConfigDict(extra="allow")

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class AnswersApiResponse(BaseModel):
    """Typed response returned by `/chat/completions`."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    object: Optional[str] = None
    created: Optional[int] = None
    model: Optional[Literal["brave", "brave-pro"]] = None
    system_fingerprint: Optional[str] = None
    choices: list[AnswersChoice] = Field(default_factory=list)
    usage: Optional[AnswersUsage] = None


class AnswersStreamingEvent(BaseModel):
    """A single parsed line from the answers streaming endpoint."""

    raw: str
    event: Optional[str] = None
    text: Optional[str] = None
    done: bool = False
    chunk: Optional[AnswersApiResponse] = None
