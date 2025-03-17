from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, Generic, Protocol, TypeVar

import numpy as np

if TYPE_CHECKING:
    from cartographer.printer import Toolhead
    from cartographer.stream import Session


class Model(Protocol):
    def distance_to_frequency(self, distance: float) -> float: ...
    def frequency_to_distance(self, frequency: float) -> float: ...


class Sample(Protocol):
    frequency: float
    time: float


S = TypeVar("S", bound=Sample)


class Mcu(Protocol, Generic[S]):
    def start_session(self, start_condition: Callable[[S], bool] | None = None) -> Session[S]: ...


class ScanProbe(Generic[S]):
    def __init__(
        self,
        mcu: Mcu[S],
        toolhead: Toolhead,
        *,
        model: Model | None = None,
        probe_height: float = 2.0,
    ) -> None:
        self._toolhead: Toolhead = toolhead
        self.model: Model | None = model
        self.probe_height: float = probe_height
        self._mcu: Mcu[S] = mcu

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
