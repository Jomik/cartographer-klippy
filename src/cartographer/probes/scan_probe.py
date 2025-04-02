from __future__ import annotations

import math
from typing import TYPE_CHECKING, Generic, Protocol

import numpy as np
from typing_extensions import override

from cartographer.printer_interface import C, Endstop, HomingState, S

if TYPE_CHECKING:
    from cartographer.printer_interface import Mcu, Toolhead
    from cartographer.stream import Session


class Model(Protocol):
    @property
    def z_offset(self) -> float: ...
    def distance_to_frequency(self, distance: float) -> float: ...
    def frequency_to_distance(self, frequency: float) -> float: ...


TRIGGER_DISTANCE = 2.0


class ScanProbe(Endstop[C], Generic[C, S]):
    """Implementation for Scan mode."""

    @property
    def z_offset(self) -> float:
        if self.model is None:
            return 0.0
        return self.model.z_offset

    def __init__(
        self,
        mcu: Mcu[C, S],
        toolhead: Toolhead,
        *,
        model: Model | None = None,
        probe_height: float = TRIGGER_DISTANCE,
    ) -> None:
        self._toolhead: Toolhead = toolhead
        self.model: Model | None = model
        self.probe_height: float = probe_height
        self._mcu: Mcu[C, S] = mcu

    def probe(self, *, speed: float) -> float:
        if not self._toolhead.is_homed("z"):
            msg = "Z axis must be homed before probing"
            raise RuntimeError(msg)
        self._toolhead.manual_move(z=self.probe_height, speed=speed)
        self._toolhead.wait_moves()
        return self.measure_distance()

    def distance_to_frequency(self, distance: float) -> float:
        if self.model is None:
            msg = "cannot convert distance to frequency without a model"
            raise RuntimeError(msg)
        return self.model.distance_to_frequency(distance)

    def measure_distance(self, *, time: float | None = None, min_sample_count: int = 10, skip_count: int = 5) -> float:
        if self.model is None:
            msg = "cannot measure distance without a model"
            raise RuntimeError(msg)
        time = time or self._toolhead.get_last_move_time()
        with self._mcu.start_session(lambda sample: sample.time >= time) as session:
            session.wait_for(lambda samples: len(samples) >= min_sample_count + skip_count)
        samples = session.get_items()[skip_count:]

        dist = float(np.median([self.model.frequency_to_distance(sample.frequency) for sample in samples]))
        if math.isinf(dist):
            msg = "toolhead stopped below model range"
            raise RuntimeError(msg)
        return dist

    @override
    def query_is_triggered(self, print_time: float = ...) -> bool:
        distance = self.measure_distance(time=print_time)
        return distance <= self.get_endstop_position()

    @override
    def get_endstop_position(self) -> float:
        return self.probe_height

    @override
    def home_start(self, print_time: float) -> C:
        trigger_frequency = self.distance_to_frequency(self.get_endstop_position())
        return self._mcu.start_homing_scan(print_time, trigger_frequency)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        if self not in homing_state.endstops:
            return
        if not homing_state.is_homing_z():
            return
        distance = self.measure_distance()

        homing_state.set_z_homed_position(distance)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu.stop_homing(home_end_time)

    def start_session(
        self,
    ) -> Session[S]:
        time = self._toolhead.get_last_move_time()
        return self._mcu.start_session(lambda sample: sample.time >= time)
