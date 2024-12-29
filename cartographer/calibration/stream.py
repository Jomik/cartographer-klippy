from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from cartographer.helpers.filter import AlphaBetaFilter
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import Sample, StreamHandler


@dataclass
class CalibrationSample:
    position: list[float]
    frequency: float
    temperature: float


def calibration_session(
    stream_handler: StreamHandler,
    mcu_helper: McuHelper,
    callback: Callable[[CalibrationSample], bool],
    completion_callback: Optional[Callable[[], None]] = None,
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
        position, _ = dump_trapq.get_trapq_position(sample.time)
        if position is None:
            logging.warning(f"No position for sample at time {sample.time}")
            return False

        calibration_sample = CalibrationSample(
            frequency=frequency,
            temperature=sample.temperature,
            position=position,
        )
        return callback(calibration_sample)

    return stream_handler.session(enrich_sample_callback, completion_callback)
