from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from cartographer.calibration.model import ScanModel
from cartographer.helpers.filter import AlphaBetaFilter
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import Sample, StreamHandler


@dataclass
class RichSample:
    time: float
    frequency: float
    temperature: float
    distance: float
    position: Optional[list[float]]
    velocity: Optional[float]


def rich_session(
    stream_handler: StreamHandler,
    mcu_helper: McuHelper,
    model: ScanModel,
    callback: Callable[[RichSample], bool],
    completion_callback: Optional[Callable[[], None]] = None,
    active: bool = True,
):
    filter = AlphaBetaFilter()
    mcu = mcu_helper.get_mcu()
    printer = mcu.get_printer()
    motion_report = printer.lookup_object("motion_report")
    dump_trapq = motion_report.trapqs.get("toolhead")
    if dump_trapq is None:
        raise printer.command_error("No dump trapq for toolhead")

    def enrich_sample_callback(sample: Sample) -> bool:
        data_smooth = filter.update(sample.time, sample.count)
        frequency = mcu_helper.count_to_frequency(data_smooth)
        distance = model.frequency_to_distance(frequency)
        position, velocity = dump_trapq.get_trapq_position(sample.time)

        # TODO: Compensate for axis twist based on position

        rich_sample = RichSample(
            time=sample.time,
            frequency=frequency,
            distance=distance,
            temperature=sample.temperature,
            position=position,
            velocity=velocity,
        )
        return callback(rich_sample)

    return stream_handler.session(enrich_sample_callback, completion_callback, active)
