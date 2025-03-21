from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from typing_extensions import override

if TYPE_CHECKING:
    from gcode import GCodeDispatch

module_name = __name__.split(".")[0]

root_logger = logging.getLogger(module_name)

formatter = logging.Formatter("[%(levelname)s:%(name)s] %(msg)s")


@final
class RootHandlerFormatter(logging.Handler):
    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            record.msg = formatter.format(record)

        except Exception:
            self.handleError(record)


def apply_logging_config():
    root_logger.addHandler(RootHandlerFormatter())


class GCodeConsoleFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(message)s")

    @override
    def format(self, record: logging.LogRecord) -> str:
        prefix = "!! " if record.levelno >= logging.ERROR else ""
        return prefix + super().format(record)


class GCodeConsoleHandler(logging.Handler):
    def __init__(self, gcode: GCodeDispatch) -> None:
        self.gcode: GCodeDispatch = gcode
        super().__init__()

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = self.format(record)
            self.gcode.respond_raw(f"{log_entry}\n")

        except Exception:
            self.handleError(record)
