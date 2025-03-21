from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generic, Protocol, final

from typing_extensions import override

from cartographer.printer_interface import C, Endstop, Mcu, S

if TYPE_CHECKING:
    from cartographer.printer_interface import HomingState

logger = logging.getLogger(__name__)

TRIGGER_DISTANCE = 2.0


class Probe(Protocol):
    def measure_distance(self, *, time: float = ...) -> float: ...
    def distance_to_frequency(self, distance: float) -> float: ...


@final
class ScanEndstop(Endstop[C], Generic[C, S]):
    """Implementation for Scan mode."""

    def __init__(self, mcu: Mcu[C, S], probe: Probe) -> None:
        self._mcu = mcu
        self._probe = probe

        self._trigger_distance = TRIGGER_DISTANCE

    @override
    def query_is_triggered(self, print_time: float = ...) -> bool:
        distance = self._probe.measure_distance(time=print_time)
        return distance <= self.get_endstop_position()

    @override
    def get_endstop_position(self) -> float:
        return self._trigger_distance

    @override
    def home_start(self, print_time: float) -> C:
        trigger_frequency = self._probe.distance_to_frequency(self.get_endstop_position())
        return self._mcu.start_homing_scan(print_time, trigger_frequency)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        if self not in homing_state.endstops:
            return
        if not homing_state.is_homing_z():
            return
        distance = self._probe.measure_distance()

        homing_state.set_z_homed_position(distance)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu.stop_homing(home_end_time)
