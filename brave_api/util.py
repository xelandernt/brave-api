import re
from datetime import datetime
from typing import Optional, List

_VALID_WEB_RESULT_FILTERS = {
    "discussions",
    "faq",
    "infobox",
    "locations",
    "news",
    "query",
    "summarizer",
    "videos",
    "web",
}
_VALID_FRESHNESS_VALUES = {"pd", "pw", "pm", "py"}


def validate_query_word_limit(v: str) -> str:
    if len(v.split()) > 50:
        raise ValueError("Query cannot have more than 50 words")
    return v


def validate_date_range(v: str) -> bool:
    if not re.match(r"^\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2}$", v):
        return False

    start, end = v.split("to")
    try:
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return False

    return True


def validate_freshness(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if v == "":
        return v
    if v in _VALID_FRESHNESS_VALUES or validate_date_range(v):
        return v
    raise ValueError(
        "Freshness must be one of pd, pw, pm, py, or a date range in the form YYYY-MM-DDtoYYYY-MM-DD"
    )


def validate_result_filter(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v

    filters = [item.strip() for item in v.split(",") if item.strip()]
    if not filters:
        raise ValueError("Result filter must contain at least one result type")

    invalid = [item for item in filters if item not in _VALID_WEB_RESULT_FILTERS]
    if invalid:
        raise ValueError(
            f"Invalid result filter values: {invalid}. Allowed values are {sorted(_VALID_WEB_RESULT_FILTERS)}"
        )

    return ",".join(filters)


def validate_location_ids(v: List[str]) -> List[str]:
    if not v:
        raise ValueError("At least one location id is required")
    if any(not item.strip() for item in v):
        raise ValueError("Location ids must be non-empty")
    if len(set(v)) != len(v):
        raise ValueError("Location ids must be unique")
    return v
