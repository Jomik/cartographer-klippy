from __future__ import annotations

import logging
from typing import final

from typing_extensions import override

from cartographer.printer import HomingState

from .base_mode import EndstopMode

logger = logging.getLogger(__name__)


@final
class NoneMode(EndstopMode):
    """An empty mode before calibration."""

    @override
    def query_triggered(self, print_time: float) -> bool:
        return True

    @override
    def get_endstop_position(self) -> float:
        return 0.0

    @override
    def home_start(self, print_time: float) -> object:
        raise RuntimeError("Cannot home before calibration.")

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        raise RuntimeError("Cannot home before calibration.")
