from __future__ import annotations

import logging
from textwrap import dedent
from typing import Protocol

from typing_extensions import override

module_name = __name__.split(".")[0]

root_logger = logging.getLogger(module_name)


class Console(Protocol):
    def respond_raw(self, msg: str) -> None: ...


def setup_console_logger(console: Console) -> logging.Handler:
    console_handler = GCodeConsoleHandler(console)
    console_handler.setFormatter(GCodeConsoleFormatter())
    console_handler.addFilter(GCodeConsoleFilter())
    root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.DEBUG)  # To allow all messages to be handled by the console handler

    return console_handler


class GCodeConsoleFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(message)s")

    @override
    def format(self, record: logging.LogRecord) -> str:
        prefix = "!! " if record.levelno >= logging.ERROR else ""
        return prefix + dedent(super().format(record)).replace("\n", " ").strip()


class GCodeConsoleFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__("%(message)s")

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        return "klipper.mcu" not in record.name or record.levelno >= logging.WARNING


class GCodeConsoleHandler(logging.Handler):
    def __init__(self, console: Console) -> None:
        self.console: Console = console
        super().__init__()

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = self.format(record)
            self.console.respond_raw(f"{log_entry}\n")

        except Exception:
            self.handleError(record)
