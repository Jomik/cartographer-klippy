from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable, Optional, Protocol

from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import Sample as StreamSample, StreamHandler

logger = logging.getLogger(__name__)


@dataclass
class Sample:
    time: float
    frequency: float
    temperature: float
    distance: float
    position: list[float]
    velocity: float


class Model(Protocol):
    def frequency_to_distance(self, frequency: float) -> float: ...


def scan_session(
    stream_handler: StreamHandler,
    mcu_helper: McuHelper,
    model: Model,
    callback: Callable[[Sample], bool],
    completion_callback: Optional[Callable[[], None]] = None,
    active: bool = True,
):
    printer = mcu_helper.get_printer()
    motion_report = printer.lookup_object("motion_report")
    dump_trapq = motion_report.trapqs.get("toolhead")
    if dump_trapq is None:
        raise printer.command_error("No dump trapq for toolhead")

    def enrich_sample_callback(sample: StreamSample) -> bool:
        distance = model.frequency_to_distance(sample.frequency)
        position, velocity = dump_trapq.get_trapq_position(sample.time)
        if position is None:
            logger.error(f"No position for sample at time {sample.time}")
            return False
        if velocity is None:
            logger.error(f"No velocity for sample at time {sample.time}")
            return False

        # TODO: Compensate for axis twist based on position

        rich_sample = Sample(
            time=sample.time,
            frequency=sample.frequency,
            distance=distance,
            temperature=sample.temperature,
            position=position,
            velocity=velocity,
        )
        return callback(rich_sample)

    return stream_handler.session(enrich_sample_callback, completion_callback, active)
