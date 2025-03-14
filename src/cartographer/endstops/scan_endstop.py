from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, final

from typing_extensions import override

from cartographer.printer import Endstop

if TYPE_CHECKING:
    from cartographer.printer import HomingState, Toolhead

logger = logging.getLogger(__name__)

TRIGGER_DISTANCE = 2.0


class Mcu(Protocol):
    def start_homing_scan(self, print_time: float, frequency: float) -> object: ...
    def stop_homing(self, home_end_time: float) -> float: ...


class Probe(Protocol):
    def measure_distance(self, *, time: float = ...) -> float: ...
    def distance_to_frequency(self, distance: float) -> float: ...


@final
class ScanEndstop(Endstop):
    """Implementation for Scan mode."""

    def __init__(self, toolhead: Toolhead, mcu: Mcu, probe: Probe) -> None:
        self._toolhead = toolhead
        self._mcu = mcu
        self._probe = probe

        self._trigger_distance = TRIGGER_DISTANCE

    @override
    def query_is_triggered(self, print_time: float) -> bool:
        distance = self._probe.measure_distance(time=print_time)
        return distance <= self.get_endstop_position()

    @override
    def get_endstop_position(self) -> float:
        return self._trigger_distance

    @override
    def home_start(self, print_time: float) -> object:
        self._toolhead.wait_moves()
        trigger_frequency = self._probe.distance_to_frequency(self.get_endstop_position())
        return self._mcu.start_homing_scan(print_time, trigger_frequency)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        if self not in homing_state.endstops:
            return
        if not homing_state.is_homing("z"):
            return
        distance = self._probe.measure_distance()

        homing_state.set_homed_position("z", distance)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu.stop_homing(home_end_time)
