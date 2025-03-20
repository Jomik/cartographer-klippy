from __future__ import annotations

import logging
from typing import Generic, Protocol, final

from typing_extensions import override

from cartographer.printer import C, Endstop, HomingState, Toolhead

logger = logging.getLogger(__name__)


class Mcu(Protocol, Generic[C]):
    def start_homing_touch(self, print_time: float, threshold: int) -> C: ...
    def stop_homing(self, home_end_time: float) -> float: ...


@final
class TouchEndstop(Endstop[C]):
    """Implementation for Survey Touch."""

    def __init__(self, toolhead: Toolhead, mcu: Mcu[C], threshold: int) -> None:
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
