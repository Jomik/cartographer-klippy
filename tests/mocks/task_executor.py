from __future__ import annotations

from typing import Callable, TypeVar

from typing_extensions import ParamSpec, override

from cartographer.interfaces.multiprocessing import TaskExecutor

P = ParamSpec("P")
R = TypeVar("R")


class InlineTaskExecutor(TaskExecutor):
    @override
    def run(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)
