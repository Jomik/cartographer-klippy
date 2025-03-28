from __future__ import annotations

import logging
from typing import Generic, final

from typing_extensions import override

from cartographer.printer_interface import C, Endstop, HomingState, Mcu, S, Toolhead

logger = logging.getLogger(__name__)


@final
class TouchEndstop(Endstop[C], Generic[C, S]):
    """Implementation for Survey Touch."""

    def __init__(self, toolhead: Toolhead, mcu: Mcu[C, S], threshold: int) -> None:
        self._toolhead = toolhead
        self._mcu = mcu
        self.threshold = threshold

    @override
    def query_is_triggered(self, print_time: float) -> bool:
        """Touch endstop is never in a triggered state."""
        return False

    @override
    def get_endstop_position(self) -> float:
        return 0

    @override
    def home_start(self, print_time: float) -> C:
        if self.threshold <= 0:
            msg = "Threshold must be greater than 0"
            raise RuntimeError(msg)
        return self._mcu.start_homing_touch(print_time, self.threshold)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        if self not in homing_state.endstops:
            return
        if not homing_state.is_homing_z():
            return

        homing_state.set_z_homed_position(0)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu.stop_homing(home_end_time)
