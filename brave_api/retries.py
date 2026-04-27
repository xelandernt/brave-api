import abc
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Final

import niquests

DEFAULT_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset(
    {429, 500, 502, 503, 504}
)
DEFAULT_RETRYABLE_EXCEPTIONS: Final[tuple[type[Exception], ...]] = (
    niquests.exceptions.ConnectionError,
    niquests.exceptions.ConnectTimeout,
    niquests.exceptions.ReadTimeout,
    niquests.exceptions.Timeout,
)
BRAVE_RATE_LIMIT_VALUE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\s*(?P<value>-?\d+(?:\.\d+)?)\s*(?:,|$)"
)


class RetryStrategy(abc.ABC):
    """Strategy interface for computing the next retry delay."""

    @abc.abstractmethod
    def get_delay(
        self,
        attempt: int,
        *,
        response: niquests.Response | niquests.AsyncResponse | None = None,
        error: Exception | None = None,
    ) -> float:
        """Get the next retry delay."""


@dataclass(frozen=True)
class FixedDelayRetryStrategy(RetryStrategy):
    delay_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")

    def get_delay(
        self,
        attempt: int,
        *,
        response: niquests.Response | niquests.AsyncResponse | None = None,
        error: Exception | None = None,
    ) -> float:
        return self.delay_seconds


@dataclass(frozen=True)
class ExponentialBackoffRetryStrategy(RetryStrategy):
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")
        if self.multiplier < 1:
            raise ValueError("multiplier must be >= 1")

    def get_delay(
        self,
        attempt: int,
        *,
        response: niquests.Response | niquests.AsyncResponse | None = None,
        error: Exception | None = None,
    ) -> float:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        delay = self.base_delay_seconds * (self.multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


@dataclass(frozen=True)
class RetryAfterRetryStrategy(RetryStrategy):
    fallback_strategy: RetryStrategy = field(
        default_factory=ExponentialBackoffRetryStrategy
    )

    @staticmethod
    def _parse_retry_after(value: str) -> float | None:
        stripped = value.strip()
        try:
            return max(0.0, float(stripped))
        except ValueError:
            pass

        try:
            retry_at = parsedate_to_datetime(stripped)
        except (TypeError, ValueError, IndexError):
            return None

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)

        return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())

    def get_delay(
        self,
        attempt: int,
        *,
        response: niquests.Response | niquests.AsyncResponse | None = None,
        error: Exception | None = None,
    ) -> float:
        if response is not None:
            headers = getattr(response, "headers", None)
            if headers is not None:
                retry_after = headers.get("Retry-After")
                if isinstance(retry_after, str):
                    parsed_delay = self._parse_retry_after(retry_after)
                    if parsed_delay is not None:
                        return parsed_delay

        return self.fallback_strategy.get_delay(attempt, response=response)


@dataclass(frozen=True)
class BraveRateLimitRetryStrategy(RetryStrategy):
    fallback_strategy: RetryStrategy = field(default_factory=RetryAfterRetryStrategy)

    @staticmethod
    def _parse_rate_limit_header(value: str) -> tuple[float, ...] | None:
        parsed_values: list[float] = []
        position = 0
        for match in BRAVE_RATE_LIMIT_VALUE_PATTERN.finditer(value):
            if match.start() != position:
                return None
            parsed_values.append(max(0.0, float(match.group("value"))))
            position = match.end()
        if position != len(value) or not parsed_values:
            return None
        return tuple(parsed_values)

    @classmethod
    def _parse_brave_rate_limit_delay(cls, headers: Mapping[str, str]) -> float | None:
        reset_header = headers.get("X-RateLimit-Reset")
        if not isinstance(reset_header, str):
            return None

        reset_values = cls._parse_rate_limit_header(reset_header)
        if reset_values is None or not reset_values:
            return None

        remaining_header = headers.get("X-RateLimit-Remaining")
        if isinstance(remaining_header, str):
            remaining_values = cls._parse_rate_limit_header(remaining_header)
            if remaining_values is not None and len(remaining_values) == len(
                reset_values
            ):
                exhausted_windows = [
                    reset_value
                    for remaining_value, reset_value in zip(
                        remaining_values, reset_values, strict=True
                    )
                    if remaining_value <= 0
                ]
                if exhausted_windows:
                    return max(exhausted_windows)

        return min(reset_values)

    def get_delay(
        self,
        attempt: int,
        *,
        response: niquests.Response | niquests.AsyncResponse | None = None,
        error: Exception | None = None,
    ) -> float:
        if response is not None:
            headers = getattr(response, "headers", None)
            if headers is not None:
                parsed_delay = self._parse_brave_rate_limit_delay(headers)
                if parsed_delay is not None:
                    return parsed_delay

        return self.fallback_strategy.get_delay(attempt, response=response)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    max_attempts: int = 3
    strategy: RetryStrategy = field(default_factory=BraveRateLimitRetryStrategy)
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_STATUS_CODES
    )
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_EXCEPTIONS
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

    def should_retry_status(self, status_code: int) -> bool:
        return status_code in self.retryable_status_codes

    def should_retry_exception(self, error: Exception) -> bool:
        return isinstance(error, self.retryable_exceptions)
