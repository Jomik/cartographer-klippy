from __future__ import annotations

import logging
from queue import Queue
import queue
from threading import Event
from types import TracebackType
from typing import Callable, Optional, Type, final

from klippy import Printer
from reactor import Reactor

from .helper import RawSample, McuHelper

BUFFER_LIMIT_DEFAULT = 100
TIMEOUT = 2.0


@final
class StreamHandler:
    _buffer: list[RawSample] = []
    _buffer_limit = BUFFER_LIMIT_DEFAULT
    _queue: Queue[list[RawSample]] = Queue()
    _flush_event = Event()
    _sessions: list[StreamSession] = []

    def __init__(self, printer: Printer, mcu_helper: McuHelper) -> None:
        self._printer = printer
        self._reactor = printer.get_reactor()
        self._mcu_helper = mcu_helper
        self._timeout_timer = self._reactor.register_timer(self._timeout)
        self._mcu_helper.get_mcu().register_response(
            self._handle_data, "cartographer_data"
        )

    def session(
        self,
        callback: Callable[[RawSample], bool],
        completion_callback: Optional[Callable[[], None]] = None,
    ) -> StreamSession:
        """
        Start a stream session to receive data

        :param callback: Should return True if the session is complete
        :param completion_callback: Called when the session is stopped
        """
        session = StreamSession(
            self._reactor,
            self._remove_session,
            callback,
            completion_callback,
        )
        self._register_session(session)
        return session

    def _handle_data(self, data: RawSample) -> None:
        self._buffer.append(data)
        self._schedule_flush()

    def _timeout(self, eventtime: float) -> float:
        if self._flush():
            return eventtime + TIMEOUT
        if not self._mcu_helper.is_streaming():
            return self._reactor.NEVER
        if not self._printer.is_shutdown():
            msg = "Cartographer stream timed out"
            logging.error(msg)
            self._printer.invoke_shutdown(msg)
        return self._reactor.NEVER

    def _register_session(self, session: StreamSession) -> None:
        if len(self._sessions) == 0:
            curtime = self._reactor.monotonic()
            self._reactor.update_timer(self._timeout_timer, curtime + TIMEOUT)
            self._mcu_helper.start_stream()
        self._sessions.append(session)

    def _remove_session(self, session: StreamSession) -> bool:
        found = session in self._sessions
        if found:
            self._sessions.remove(session)
        if not self._sessions:
            self._mcu_helper.stop_stream()
            self._reactor.update_timer(self._timeout_timer, Reactor.NEVER)
        return found

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

        logging.info("Scheduling flush")
        self._reactor.register_async_callback(wrapped_flush)

    def _flush(self) -> bool:
        self._flush_event.clear()
        updated_timer = False
        while True:
            try:
                samples = self._queue.get_nowait()
                updated_timer = False
                for sample in samples:
                    if not updated_timer:
                        curtime = self._reactor.monotonic()
                        self._reactor.update_timer(
                            self._timeout_timer, curtime + TIMEOUT
                        )
                        updated_timer = True
                    self._flush_message(sample)
            except queue.Empty:
                return updated_timer

    def _flush_message(self, sample: RawSample) -> None:
        for session in self._sessions:
            session.handle(sample)


@final
class StreamSession:
    def __init__(
        self,
        reactor: Reactor,
        remove_session: Callable[[StreamSession], bool],
        callback: Callable[[RawSample], bool],
        completion_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self._callback = callback
        self._completion_callback = completion_callback
        self._completion = reactor.completion()
        self._remove_session = remove_session

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ):
        self.stop()

    def handle(self, sample: RawSample) -> None:
        if self._callback(sample):
            self._completion.complete(())

    def stop(self):
        if not self._remove_session(self):
            return
        if self._completion_callback is not None:
            self._completion_callback()

    def wait(self):
        _ = self._completion.wait()
        self.stop()
