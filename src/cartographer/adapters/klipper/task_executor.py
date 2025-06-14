from __future__ import annotations

import multiprocessing
from typing import TYPE_CHECKING, Callable, TypeVar, final

from typing_extensions import ParamSpec, override

from cartographer.interfaces.multiprocessing import TaskExecutor

if TYPE_CHECKING:
    from multiprocessing.connection import Connection

    from reactor import Reactor

P = ParamSpec("P")
R = TypeVar("R")

WAIT_TIME = 0.1


@final
class KlipperMultiprocessingExecutor(TaskExecutor):
    def __init__(self, reactor: Reactor) -> None:
        self._reactor = reactor

    @override
    def run(self, fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        def worker(child_conn: Connection):
            try:
                result = fn(*args, **kwargs)
                child_conn.send((False, result))
            except Exception as e:
                child_conn.send((True, e))
            finally:
                child_conn.close()

        parent_conn, child_conn = multiprocessing.Pipe()
        proc = multiprocessing.Process(target=worker, args=(child_conn,), daemon=True)
        proc.start()

        eventtime = self._reactor.monotonic()
        while proc.is_alive():
            eventtime = self._reactor.pause(eventtime + WAIT_TIME)

        proc.join()
        is_err, payload = parent_conn.recv()
        parent_conn.close()

        if is_err:
            raise payload from None  # Raise the original exception
        return payload
