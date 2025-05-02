from functools import wraps
from typing import Callable, TypeVar

from gcode import CommandError
from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def reraise_as_command_error(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except RuntimeError as e:
            raise CommandError(str(e)) from e

    return wrapper
