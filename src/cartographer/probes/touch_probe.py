from __future__ import annotations

import logging
from typing import final

from typing_extensions import override

from cartographer.printer_interface import C, Endstop, HomingState, Mcu, S, Toolhead

logger = logging.getLogger(__name__)


@final
class TouchProbe(Endstop[C]):
    """Implementation for Survey Touch."""

    def __init__(
        self,
        mcu: Mcu[C, S],
        toolhead: Toolhead,
        *,
        threshold: int,
    ) -> None:
        self._toolhead = toolhead
        self._mcu = mcu
        self.threshold = threshold
        self.probe_height = 5.0

    def probe(self, *, speed: float) -> float:
        if not self._toolhead.is_homed("z"):
            msg = "Z axis must be homed before probing"
            raise RuntimeError(msg)
        self._toolhead.manual_move(z=self.probe_height, speed=speed)
        self._toolhead.wait_moves()
        distance = self._toolhead.z_homing_move(self, bottom=-2.0, speed=3.0)
        return distance

    @override
    def query_is_triggered(self, print_time: float) -> bool:
        # Touch endstop is never in a triggered state.
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
