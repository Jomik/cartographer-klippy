from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Generic, Protocol, TypeVar, final

T = TypeVar("T")


class Condition(Protocol):
    def notify_all(self) -> None:
        """Wakes all threads waiting on this condition."""

    def wait_for(self, predicate: Callable[[], bool]) -> None:
        """Wait until a condition evaluates to True."""
        ...


@final
class Session(Generic[T]):
    def __init__(
        self,
        stream: Stream[T],
        condition: Condition,
        start_condition: Callable[[T], bool] | None = None,
    ):
        self.stream = stream
        self.items: list[T] = []
        self.start_condition = start_condition
        self._condition = condition

    def add_item(self, item: T):
        """Adds an item to the session only after the start condition is met."""
        if self.start_condition is not None:
            if not self.start_condition(item):
                return
            self.start_condition = None

        self.items.append(item)
        self._condition.notify_all()

    def wait_for(self, condition: Callable[[list[T]], bool]):
        """Waits until the given condition function returns True."""
        self._condition.wait_for(lambda: condition(self.items))

    def get_items(self) -> list[T]:
        """Returns collected items after session ends."""
        return self.items

    def __enter__(self):
        return self  # Allows using `with session:`

    def __exit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ):
        """Automatically remove session from stream when exiting the with-block."""
        self.stream.end_session(self)


class Stream(ABC, Generic[T]):
    def __init__(self, smoothing_fn: Callable[[T], T] | None = None):
        """Initializes a stream with optional smoothing function."""
        self.smoothing_fn: Callable[[T], T] | None = smoothing_fn
        self.sessions: set[Session[T]] = set()
        self.callbacks: set[Callable[[T], None]] = set()

    @abstractmethod
    def condition(self) -> Condition: ...

    def start_session(self, start_condition: Callable[[T], bool] | None = None) -> Session[T]:
        """Starts a session with an optional start condition.

        All items before the start condition will be skipped.
        """
        session = Session(self, self.condition(), start_condition)
        self.sessions.add(session)
        return session

    def end_session(self, session: Session[T]):
        """Ends a session and removes it from active sessions."""
        self.sessions.discard(session)

    def register_callback(self, callback: Callable[[T], None]):
        """Registers a callback to the stream."""
        self.callbacks.add(callback)

    def unregister_callback(self, callback: Callable[[T], None]):
        """Removes the callback from the stream."""
        self.callbacks.discard(callback)

    def add_item(self, item: T):
        """Pushes the item to all active sessions."""

        if self.smoothing_fn is not None:
            item = self.smoothing_fn(item)

        for session in self.sessions:
            session.add_item(item)

        for callback in self.callbacks:
            callback(item)
