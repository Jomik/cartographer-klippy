from __future__ import annotations

import logging
from typing_extensions import override

module_name = __name__.split(".")[0]

root_logger = logging.getLogger(module_name)

formatter = logging.Formatter("[%(levelname)s:%(name)s] %(msg)s")


class FormatLogFilter(logging.Filter):
    @override
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = formatter.format(record)
        return True


custom_filter = FormatLogFilter()
root_logger.addFilter(custom_filter)


def apply_logging_config():
    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith(module_name):
            logger = logging.getLogger(logger_name)
            logger.addFilter(custom_filter)
