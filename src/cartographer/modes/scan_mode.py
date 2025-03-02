from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.modes.base_mode import EndstopMode

if TYPE_CHECKING:
    from cartographer.printer import HomingState, Toolhead
    from cartographer.stream import Session

logger = logging.getLogger(__name__)

TRIGGER_DISTANCE = 2.0


class Model(Protocol):
    def distance_to_frequency(self, distance: float) -> float: ...
    def frequency_to_distance(self, frequency: float) -> float: ...


@dataclass
class Sample:
    time: float
    frequency: float
    temperature: float


class Mcu(Protocol):
    def start_homing_scan(self, print_time: float, frequency: float) -> object: ...
    def start_session(self, start_condition: Callable[[Sample], bool] | None = None) -> Session[Sample]: ...


@final
class ScanMode(EndstopMode):
    """Implementation for Scan mode."""

    def __init__(
        self,
        toolhead: Toolhead,
        mcu: Mcu,
        model: Model,
    ) -> None:
        self._toolhead = toolhead
        self._mcu = mcu
        self._model = model

        self._trigger_distance = TRIGGER_DISTANCE
        self._is_homing = False

    @override
    def can_switch(self) -> bool:
        return not self._is_homing

    @override
    def query_triggered(self, print_time: float) -> bool:
        with self._mcu.start_session() as session:
            session.wait_for(lambda samples: len(samples) > 0)
        samples = session.get_items()
        distance = self._model.frequency_to_distance(samples[0].frequency)
        return distance <= self.get_endstop_position()

    @override
    def get_endstop_position(self) -> float:
        return self._trigger_distance

    @override
    def home_start(self, print_time: float) -> object:
        self._is_homing = True
        self._toolhead.wait_moves()
        trigger_frequency = self._model.distance_to_frequency(self.get_endstop_position())
        return self._mcu.start_homing_scan(print_time, trigger_frequency)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        if not self._is_homing:
            return
        if not homing_state.is_homing("z"):
            return
        last_move_time = self._toolhead.get_last_move_time()
        skip = 5
        count = 10
        with self._mcu.start_session(lambda sample: sample.time >= last_move_time) as session:
            session.wait_for(lambda samples: len(samples) >= count + skip)
        samples = session.get_items()[skip:]

        dist = float(np.median([self._model.frequency_to_distance(sample.frequency) for sample in samples]))
        if math.isinf(dist):
            msg = "toolhead stopped below model range"
            raise RuntimeError(msg)

        logger.debug("Setting homed distance to %.2F", dist)
        homing_state.set_homed_position("z", dist)

        self._is_homing = False
