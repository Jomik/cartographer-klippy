from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.printer_interface import Macro, MacroParams, Toolhead

if TYPE_CHECKING:
    from cartographer.configuration import Configuration
    from cartographer.probe import Probe

logger = logging.getLogger(__name__)


@dataclass
class CalibrationOptions:
    start: float
    end: float
    axis: float


class AxisTwistCompensationHelper(Protocol):
    move_height: float
    speed: float

    def clear_compensations(self, axis: Literal["x", "y"]) -> None: ...
    def save_compensations(self, axis: Literal["x", "y"], start: float, end: float, values: list[float]) -> None: ...
    def get_calibration_options(self, axis: Literal["x", "y"]) -> CalibrationOptions: ...


@final
class AxisTwistCompensationMacro(Macro[MacroParams]):
    name = "TOUCH_AXIS_TWIST_COMPENSATION"
    description = "Scan and touch to calculate axis twist compensation values."

    def __init__(
        self, probe: Probe, toolhead: Toolhead, helper: AxisTwistCompensationHelper, config: Configuration
    ) -> None:
        self.probe = probe
        self.toolhead = toolhead
        self.helper = helper
        self.config = config

    @override
    def run(self, params: MacroParams) -> None:
        axis = params.get("AXIS", default="x").lower()
        if axis not in ("x", "y"):
            msg = f"invalid axis '{axis}'"
            raise RuntimeError(msg)
        sample_count = params.get_int("SAMPLE_COUNT", default=5)
        calibration = self.helper.get_calibration_options(axis)
        self.helper.clear_compensations(axis)

        try:
            self._calibrate(axis, sample_count, calibration)
        except RuntimeError:
            logger.info("""
                Error during axis twist compensation calibration,
                existing compensation has been cleared.
                Restart firmware to restore.
                """)
            raise

    def _calibrate(self, axis: Literal["x", "y"], sample_count: int, calibration: CalibrationOptions) -> None:
        step = (calibration.end - calibration.start) / (sample_count - 1)
        results: list[float] = []
        start_time = time.time()
        for i in range(sample_count):
            position = calibration.start + i * step
            self._move_probe_to(axis, position, calibration.axis)
            scan = self.probe.perform_scan()
            self._move_nozzle_to(axis, position, calibration.axis)
            touch = self.probe.perform_touch()
            result = scan - touch
            logger.debug("Offset at %:.2f: %.6f", position, result)
            results.append(result)
        logger.debug("Axis twist measurements completed in %.2f seconds", time.time() - start_time)

        avg = float(np.mean(results))
        results = [avg - x for x in results]

        self.helper.save_compensations(axis, calibration.start, calibration.end, results)
        logger.info("""
            AXIS_TWIST_COMPENSATION state has been saved
            for the current session.  The SAVE_CONFIG command will
            update the printer config file and restart the printer.
            """)
        logger.info(
            "Touch %s axis twist compensation calibration complete: mean z_offset: %.6f, offsets: (%s)",
            axis.upper(),
            avg,
            ", ".join(f"{s:.6f}" for s in results),
        )

    def _move_nozzle_to(self, axis: Literal["x", "y"], position: float, calibration_axis: float) -> None:
        self.toolhead.move(z=self.helper.move_height, speed=self.helper.speed)
        if axis == "x":
            self.toolhead.move(
                x=position,
                y=calibration_axis,
                speed=self.helper.speed,
            )
        else:
            self.toolhead.move(
                x=calibration_axis,
                y=position,
                speed=self.helper.speed,
            )

    def _move_probe_to(self, axis: Literal["x", "y"], position: float, calibration_axis: float) -> None:
        if axis == "x":
            self.toolhead.move(
                x=position - self.config.x_offset,
                y=calibration_axis - self.config.y_offset,
                speed=self.helper.speed,
            )
        else:
            self.toolhead.move(
                x=calibration_axis - self.config.x_offset,
                y=position - self.config.y_offset,
                speed=self.helper.speed,
            )
