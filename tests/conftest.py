import os
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import pytest

from brave_api.constants import BRAVE_API_KEY_ENV_VAR

P = ParamSpec("P")
R = TypeVar("R")


def live(test_func: Callable[P, R]) -> Callable[P, R]:
    pytest.mark.live(test_func)
    pytest.mark.skipif(
        not os.getenv(BRAVE_API_KEY_ENV_VAR),
        reason="BRAVE_API_KEY is not set",
    )(test_func)
    return test_func
