from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.configuration import TouchModelConfiguration
from cartographer.printer_interface import Macro, MacroParams, Position
from cartographer.probe.touch_mode import TouchError, TouchMode

if TYPE_CHECKING:
    from cartographer.printer_interface import Toolhead


logger = logging.getLogger(__name__)

Probe = TouchMode[object]

logger = logging.getLogger(__name__)


class Configuration(Protocol):
    def save_new_touch_model(self, name: str, speed: float, threshold: int) -> TouchModelConfiguration: ...


@final
class TouchMacro(Macro[MacroParams]):
    name = "TOUCH"
    description = "Touch the bed to get the height offset at the current position."
    last_trigger_position: float = 0

    def __init__(self, probe: Probe) -> None:
        self._probe = probe

    @override
    def run(self, params: MacroParams) -> None:
        trigger_position = self._probe.perform_probe()
        logger.info("Result is z=%.6f", trigger_position)
        self.last_trigger_position = trigger_position


@final
class TouchAccuracyMacro(Macro[MacroParams]):
    name = "TOUCH_ACCURACY"
    description = "Touch the bed multiple times to measure the accuracy of the probe."

    def __init__(self, probe: Probe, toolhead: Toolhead) -> None:
        self._probe = probe
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        lift_speed = params.get_float("LIFT_SPEED", 5.0, above=0)
        retract = params.get_float("SAMPLE_RETRACT_DIST", 1.0, minval=0)
        sample_count = params.get_int("SAMPLES", 5, minval=1)
        position = self._toolhead.get_position()

        logger.info(
            "TOUCH_ACCURACY at X:%.3f Y:%.3f Z:%.3f (samples=%d retract=%.3f lift_speed=%.1f)",
            position.x,
            position.y,
            position.z,
            sample_count,
            retract,
            lift_speed,
        )

        self._toolhead.move(z=position.z + retract, speed=lift_speed)
        measurements: list[float] = []
        while len(measurements) < sample_count:
            trigger_pos = self._probe.perform_probe()
            measurements.append(trigger_pos)
            pos = self._toolhead.get_position()
            self._toolhead.move(z=pos.z + retract, speed=lift_speed)
        logger.debug("Measurements gathered: %s", measurements)

        max_value = max(measurements)
        min_value = min(measurements)
        range_value = max_value - min_value
        avg_value = np.mean(measurements)
        median = np.median(measurements)
        std_dev = np.std(measurements)

        logger.info(
            """touch accuracy results: maximum %.6f, minimum %.6f, range %.6f, \
            average %.6f, median %.6f, standard deviation %.6f""",
            max_value,
            min_value,
            range_value,
            avg_value,
            median,
            std_dev,
        )


@final
class TouchHomeMacro(Macro[MacroParams]):
    name = "TOUCH_HOME"
    description = "Touch the bed to get the height offset at the current position."

    def __init__(
        self,
        probe: Probe,
        toolhead: Toolhead,
        home_position: Position,
    ) -> None:
        self._probe = probe
        self._toolhead = toolhead
        self._home_position = home_position

    @override
    def run(self, params: MacroParams) -> None:
        self._toolhead.move(
            x=self._home_position.x,
            y=self._home_position.y,
            speed=self._probe.config.move_speed,
        )
        trigger_pos = self._probe.perform_probe()
        pos = self._toolhead.get_position()
        self._toolhead.set_z_position(pos.z - (trigger_pos - self._probe.offset.z))
        logger.info(
            "Touch home at (%.3f,%.3f) adjusted z by %.3f, offset %.3f",
            pos.x,
            pos.y,
            -trigger_pos,
            -self._probe.offset.z,
        )


@final
class CalibrationModel(TouchModelConfiguration):
    name = "calibration"
    z_offset = 0.0

    def __init__(self, *, speed: float, threshold: int) -> None:
        self.speed = speed
        self.threshold = threshold

    @override
    def save_z_offset(self, new_offset: float) -> None:
        msg = "calibration model cannot be saved"
        raise RuntimeError(msg)


@final
class TouchCalibrateMacro(Macro[MacroParams]):
    name = "TOUCH_CALIBRATE"
    description = "Run the touch calibration"

    def __init__(self, probe: Probe, toolhead: Toolhead, config: Configuration, home_position: Position) -> None:
        self._probe = probe
        self._toolhead = toolhead
        self._config = config
        self._home_position = home_position

    @override
    def run(self, params: MacroParams) -> None:
        name = params.get("MODEL_NAME", "default")
        speed = params.get_int("SPEED", default=3, minval=1, maxval=5)
        threshold_start = params.get_int("THRESHOLD", default=500)
        threshold_max = params.get_int("MAX_THRESHOLD", default=5000)
        step = params.get_int("THRESHOLD_STEP", default=500)

        self._toolhead.move(
            x=self._home_position.x,
            y=self._home_position.y,
            speed=self._probe.config.move_speed,
        )

        logger.info("Touch calibration at speed %d", speed, threshold_start)

        model: TouchModelConfiguration | None = None
        with self._revert_model():
            for threshold in range(threshold_start, threshold_max, step):
                self._probe.model = CalibrationModel(speed=speed, threshold=threshold)
                try:
                    logger.info("Attempting touch at threshold %d", threshold)
                    _ = self._probe.perform_probe()
                    model = self._config.save_new_touch_model(name, speed, threshold)
                    break

                except TouchError:
                    logger.info("Touch failed at threshold %d", threshold)
                    continue
        if model is None:
            msg = "failed to calibrate touch probe"
            raise RuntimeError(msg)

        logger.info("Touch calibrated at speed %d, threshold %d", model.speed, model.threshold)
        self._probe.model = model

    @contextmanager
    def _revert_model(self):
        old_model = self._probe.model
        try:
            yield
        finally:
            self._probe.model = old_model
