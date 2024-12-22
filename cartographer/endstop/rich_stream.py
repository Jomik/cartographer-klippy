from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from cartographer.mcu.helper import McuHelper, RawSample
from cartographer.mcu.stream import StreamHandler

from .filter import AlphaBetaFilter
from .model import ScanModel


@dataclass
class RichSample:
    time: float
    frequency: float
    temperature: float
    distance: float
    position: Optional[list[float]]
    velocity: Optional[float]


ALPHA = 0.5
BETA = 1e-6


def rich_session(
    stream_handler: StreamHandler,
    mcu_helper: McuHelper,
    model: ScanModel,
    callback: Callable[[RichSample], bool],
    completion_callback: Optional[Callable[[], None]] = None,
):
    filter = AlphaBetaFilter(ALPHA, BETA)
    mcu = mcu_helper.get_mcu()
    printer = mcu.get_printer()
    motion_report = printer.lookup_object("motion_report")
    dump_trapq = motion_report.trapqs.get("toolhead")
    if dump_trapq is None:
        raise printer.command_error("No dump trapq for toolhead")

    def enrich_sample_callback(sample: RawSample) -> bool:
        clock = sample["clock64"]
        time = mcu.clock_to_print_time(clock)
        count = sample["data"]
        data_smooth = filter.update(time, count)
        frequency = mcu_helper.count_to_frequency(data_smooth)
        distance = model.frequency_to_distance(frequency)
        position, velocity = dump_trapq.get_trapq_position(time)

        # TODO: Compensate for axis twist based on position

        rich_sample = RichSample(
            time=time,
            frequency=frequency,
            distance=distance,
            temperature=sample["temp"],
            position=position,
            velocity=velocity,
        )
        return callback(rich_sample)

    return stream_handler.session(enrich_sample_callback, completion_callback)
