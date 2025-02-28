from __future__ import annotations

from typing import Callable, TypeVar, final

import greenlet
from reactor import Reactor
from typing_extensions import override

from cartographer.stream import Condition, Stream


@final
class KlipperCondition(Condition):
    """The Klipper equivalent of [threading.Condition](https://docs.python.org/3/library/threading.html#condition-objects)"""

    def __init__(self, reactor: Reactor):
        self.reactor = reactor
        self.waiting: list[greenlet.greenlet] = []

    @override
    def notify_all(self):
        for wait in self.waiting:
            self.reactor.update_timer(wait.timer, self.reactor.NOW)

    @override
    def wait_for(self, predicate: Callable[[], bool]) -> None:
        wait = greenlet.getcurrent()
        self.waiting.append(wait)
        while True:
            if predicate():
                break
            _ = self.reactor.pause(self.reactor.NEVER)
        self.waiting.remove(wait)


T = TypeVar("T")


@final
class KlipperStream(Stream[T]):
    def __init__(self, reactor: Reactor):
        self.reactor = reactor
        super().__init__()

    @override
    def condition(self) -> Condition:
        return KlipperCondition(self.reactor)
