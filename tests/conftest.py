import os
from collections.abc import Callable
from typing import TypeVar, cast

import pytest

from brave_api.constants import BRAVE_API_KEY_ENV_VAR

F = TypeVar("F", bound=Callable[..., object])


def live(test_func: F) -> F:
    decorated = pytest.mark.skipif(
        not os.getenv(BRAVE_API_KEY_ENV_VAR),
        reason="BRAVE_API_KEY is not set",
    )(pytest.mark.live(test_func))
    return cast(F, decorated)
