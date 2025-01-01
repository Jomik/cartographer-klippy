from __future__ import annotations

import logging
import queue
from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Event
from types import TracebackType
from typing import (
    Callable,
    Optional,
    Type,
    TypedDict,
)

from klippy import Printer
from reactor import Reactor, ReactorCompletion, ReactorTimer
from typing_extensions import override

from cartographer.helpers.filter import AlphaBetaFilter
from cartographer.mcu.helper import McuHelper

BUFFER_LIMIT_DEFAULT = 100
TIMEOUT = 2.0

logger = logging.getLogger(__name__)


class _RawSample(TypedDict):
    clock: int
    data: int
    temp: int


@dataclass
class Sample:
    clock: int
    count: int
    time: float
    temperature: float
    frequency: float


class StreamHandler:
    _printer: Printer
    _reactor: Reactor
    _mcu_helper: McuHelper
    _timeout_timer: ReactorTimer
    _filter: AlphaBetaFilter = AlphaBetaFilter()

    def __init__(self, printer: Printer, mcu_helper: McuHelper) -> None:
        self._printer = printer
        self._reactor = printer.get_reactor()
        self._mcu_helper = mcu_helper
        self._timeout_timer = self._reactor.register_timer(self._timeout)
        self._mcu_helper.get_mcu().register_response(
            self._handle_data, "cartographer_data"
        )

        self._buffer: list[_RawSample] = []
        self._buffer_limit: int = BUFFER_LIMIT_DEFAULT
        self._queue: queue.Queue[list[_RawSample]] = queue.Queue()
        self._flush_event: Event = Event()
        self._sessions: list[StreamSession] = []

    def session(
        self,
        callback: Callable[[Sample], bool],
        completion_callback: Optional[Callable[[], None]] = None,
        active: bool = True,
    ) -> StreamSession:
        """
        Start a stream session to receive data

        :param callback: Should return True if the session is complete
        :param completion_callback: Called when the session is stopped
        :param active: If False, the session will not start streaming
        """
        session = StreamSession(
            self._reactor,
            self._remove_session,
            callback,
            completion_callback,
            active,
        )
        self._register_session(session)
        return session

    def _handle_data(self, data: _RawSample) -> None:
        self._buffer.append(data)
        self._schedule_flush()

    def _timeout(self, eventtime: float) -> float:
        if self._flush():
            return eventtime + TIMEOUT
        if not self._mcu_helper.is_streaming():
            return self._reactor.NEVER
        if not self._printer.is_shutdown():
            msg = "Cartographer stream timed out"
            logger.error(msg)
            self._printer.invoke_shutdown(msg)
        return self._reactor.NEVER

    def _count_active_sessions(self) -> int:
        return sum(1 for session in self._sessions if session.is_active())

    def _register_session(self, session: StreamSession) -> None:
        self._sessions.append(session)
        if session.is_active() and self._count_active_sessions() == 1:
            curtime = self._reactor.monotonic()
            self._reactor.update_timer(self._timeout_timer, curtime + TIMEOUT)
            self._mcu_helper.start_stream()

    def _remove_session(self, session: StreamSession) -> bool:
        found = session in self._sessions
        if not found:
            return False

        self._sessions.remove(session)
        if session.is_active() and self._count_active_sessions() == 0:
            self._mcu_helper.stop_stream()
            self._reactor.update_timer(self._timeout_timer, Reactor.NEVER)
        return True

    def _schedule_flush(self):
        if self._mcu_helper.is_streaming() and len(self._buffer) < self._buffer_limit:
            return

        self._queue.put_nowait(self._buffer)
        self._buffer = []

        if self._flush_event.is_set():
            return
        self._flush_event.set()

        def wrapped_flush(_: float) -> None:
            _ = self._flush()

        self._reactor.register_async_callback(wrapped_flush)

    def _flush(self) -> bool:
        self._flush_event.clear()
        updated_timer = False

        while True:
            try:
                samples = self._queue.get_nowait()
                logger.debug(f"Flushing {len(samples)} samples")

                if samples:
                    curtime = self._reactor.monotonic()
                    self._reactor.update_timer(self._timeout_timer, curtime + TIMEOUT)
                    updated_timer = True

                for sample in samples:
                    self._process_sample(sample)
            except queue.Empty:
                break

        return updated_timer

    def _process_sample(self, raw: _RawSample) -> None:
        sample = self._convert_sample(raw)
        for session in self._sessions:
            session.handle(sample)

    def _convert_sample(self, raw: _RawSample) -> Sample:
        count = raw["data"]
        clock = self._mcu_helper.get_mcu().clock32_to_clock64(raw["clock"])
        time = self._mcu_helper.get_mcu().clock_to_print_time(clock)
        temp = self._mcu_helper.calculate_sample_temperature(raw["temp"])

        smoothed_count = self._filter.update(time, count)
        frequency = self._mcu_helper.count_to_frequency(smoothed_count)

        return Sample(
            count=count,
            clock=clock,
            frequency=frequency,
            time=time,
            temperature=temp,
        )


class StreamCondition(ABC):
    def __init__(self, printer: Printer) -> None:
        self._completion: ReactorCompletion[None] = printer.get_reactor().completion()

    @abstractmethod
    def update(self, sample: Sample) -> None: ...

    def complete(self) -> None:
        if self._completion.test():
            return
        logger.debug(f"{self} completed")
        self._completion.complete(None)

    def wait(self) -> None:
        self._completion.wait()


class TimeCondition(StreamCondition):
    def __init__(self, printer: Printer, time: float) -> None:
        super().__init__(printer)
        self._time: float = time

    @override
    def update(self, sample: Sample) -> None:
        if sample.time >= self._time:
            self.complete()

    @override
    def __str__(self) -> str:
        return f"TimeCondition({self._time})"


class SampleCountCondition(StreamCondition):
    def __init__(self, printer: Printer, count: int) -> None:
        super().__init__(printer)
        self._count: int = count

    @override
    def update(self, sample: Sample) -> None:
        self._count -= 1
        if self._count <= 0:
            self.complete()

    @override
    def __str__(self) -> str:
        return f"SampleCountCondition({self._count})"


class StreamSession:
    _remove_session: Callable[[StreamSession], bool]
    _callback: Callable[[Sample], bool]
    _completion_callback: Optional[Callable[[], None]]
    _active: bool
    _completion: ReactorCompletion[None]

    def __init__(
        self,
        reactor: Reactor,
        remove_session: Callable[[StreamSession], bool],
        callback: Callable[[Sample], bool],
        completion_callback: Optional[Callable[[], None]],
        active: bool,
    ) -> None:
        self._callback = callback
        self._completion_callback = completion_callback
        self._completion = reactor.completion()
        self._remove_session = remove_session
        self._active = active
        self._conditions: list[StreamCondition] = []

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ):
        self.stop()

    def is_active(self) -> bool:
        return self._active

    def handle(self, sample: Sample) -> None:
        for condition in self._conditions:
            condition.update(sample)
        if self._callback(sample):
            self._completion.complete(None)

    def stop(self):
        if not self._remove_session(self):
            return
        if self._completion_callback is not None:
            self._completion_callback()
        logger.debug("Session stopped")

    def wait(self):
        _ = self._completion.wait()
        self.stop()

    def wait_for(self, condition: StreamCondition):
        logger.debug(f"Waiting for {condition}")
        self._conditions.append(condition)
        condition.wait()
        self._conditions.remove(condition)
        logger.debug(f"Continuing from {condition}")
