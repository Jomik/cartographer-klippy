import logging
import time
from functools import wraps
from typing import Callable, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def log_duration(message: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                func_logger = logging.getLogger(func.__module__)
                func_logger.debug("%s completed in %.2f seconds", message, duration)

        return wrapper

    return decorator
