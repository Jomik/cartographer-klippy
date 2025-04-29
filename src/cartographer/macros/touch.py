from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.configuration import TouchModelConfiguration
from cartographer.lib.statistics import compute_mad
from cartographer.printer_interface import Macro, MacroParams
from cartographer.probe.touch_mode import STD_TOLERANCE, TouchMode

if TYPE_CHECKING:
    from cartographer.printer_interface import Toolhead


logger = logging.getLogger(__name__)

Probe = TouchMode[object]

logger = logging.getLogger(__name__)


class Configuration(Protocol):
    zero_reference_position: tuple[float, float]
    touch_samples: int
    move_speed: float

    def save_new_touch_model(self, name: str, speed: float, threshold: int) -> TouchModelConfiguration: ...


@final
class TouchMacro(Macro[MacroParams]):
    name = "TOUCH"
    description = "Touch the bed to get the height offset at the current position."
    last_trigger_position: float | None = None

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
        logger.debug("Measurements gathered: %s", ", ".join(f"{m:.6f}" for m in measurements))

        max_value = max(measurements)
        min_value = min(measurements)
        range_value = max_value - min_value
        avg_value = np.mean(measurements)
        median = np.median(measurements)
        std_dev = np.std(measurements)
        mad = compute_mad(measurements)

        logger.info(
            """
            touch accuracy results: maximum %.6f, minimum %.6f, range %.6f,
            average %.6f, median %.6f, standard deviation %.6f
            median absolute deviation %.6f
            """,
            max_value,
            min_value,
            range_value,
            avg_value,
            median,
            std_dev,
            mad,
        )


@final
class TouchHomeMacro(Macro[MacroParams]):
    name = "TOUCH_HOME"
    description = "Touch the bed to home Z axis"

    def __init__(
        self,
        probe: Probe,
        toolhead: Toolhead,
        home_position: tuple[float, float],
    ) -> None:
        self._probe = probe
        self._toolhead = toolhead
        self._home_position = home_position

    @override
    def run(self, params: MacroParams) -> None:
        if not self._toolhead.is_homed("x") or not self._toolhead.is_homed("y"):
            msg = "must home x and y before touch homing"
            raise RuntimeError(msg)

        self._toolhead.move(
            x=self._home_position[0],
            y=self._home_position[1],
            speed=self._probe.config.move_speed,
        )
        self._toolhead.wait_moves()

        forced_z = False
        if not self._toolhead.is_homed("z"):
            forced_z = True
            _, z_max = self._toolhead.get_z_axis_limits()
            self._toolhead.set_z_position(z=z_max - 10)

        try:
            trigger_pos = self._probe.perform_probe()
        finally:
            if forced_z:
                self._toolhead.clear_z_homing_state()

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


SAFE_TRIGGER_MIN_HEIGHT = -0.2  # Initial home too far
MAD_TOLERANCE = STD_TOLERANCE * 0.6745  # Convert std to mad

MIN_ALLOWED_STEP = 75
MAX_ALLOWED_STEP = 500


def compute_step_increase(current_threshold: int, score: float) -> int:
    # Compute max allowed step from threshold
    allowed_step = (current_threshold * 0.06) ** 1.15
    allowed_max_step = max(MIN_ALLOWED_STEP, min(MAX_ALLOWED_STEP, allowed_step))

    # Compute step directly based on how bad the score is
    ratio = max(1.0, score / MAD_TOLERANCE)
    raw_step = allowed_max_step * (1 - (1 / ratio))

    # Clamp and return
    step = int(round(min(allowed_max_step, max(MIN_ALLOWED_STEP, raw_step))))
    return step


@final
class TouchCalibrateMacro(Macro[MacroParams]):
    name = "TOUCH_CALIBRATE"
    description = "Run the touch calibration"

    def __init__(self, probe: Probe, toolhead: Toolhead, config: Configuration) -> None:
        self._probe = probe
        self._toolhead = toolhead
        self._config = config

    @override
    def run(self, params: MacroParams) -> None:
        name = params.get("MODEL_NAME", "default")
        speed = params.get_int("SPEED", default=3, minval=1, maxval=5)
        threshold_start = params.get_int("START", default=500, minval=100)
        threshold_max = params.get_int("MAX", default=3000, minval=threshold_start)

        if not self._toolhead.is_homed("x") or not self._toolhead.is_homed("y"):
            msg = "must home x and y before calibration"
            raise RuntimeError(msg)

        self._toolhead.move(
            x=self._config.zero_reference_position[0],
            y=self._config.zero_reference_position[1],
            speed=self._config.move_speed,
        )
        self._toolhead.wait_moves()

        forced_z = False
        if not self._toolhead.is_homed("z"):
            forced_z = True
            _, z_max = self._toolhead.get_z_axis_limits()
            self._toolhead.set_z_position(z=z_max - 10)

        logger.info(
            "Starting touch calibration at speed %d, starting threshold %d, max threshold %d",
            speed,
            threshold_start,
            threshold_max,
        )
        try:
            threshold = self._find_acceptable_threshold(threshold_start, threshold_max, speed)
        finally:
            if forced_z:
                self._toolhead.clear_z_homing_state()

        if threshold is None:
            logger.info(
                """
                Failed to calibrate touch with thresholds between %d and %d.
                If you want to continue calibration, increase the max threshold.
                E.g. %s START=%d MAX=%d
                """,
                threshold_start,
                threshold_max,
                self.name,
                threshold_max,
                threshold_max + 1000,
            )
            return

        logger.info("Touch calibrated at speed %d, threshold %d", speed, threshold)
        self._probe.model = self._config.save_new_touch_model(name, speed, threshold)
        logger.info(
            """
            Touch model %s has been saved
            for the current session. The SAVE_CONFIG command will
            update the printer config file and restart the printer.
            """,
            name,
        )

    def _find_acceptable_threshold(self, threshold_start: int, threshold_max: int, speed: int) -> int | None:
        current_threshold = threshold_start
        while current_threshold <= threshold_max:
            model = CalibrationModel(speed=speed, threshold=current_threshold)
            score, samples = self._evaluate_threshold(model)

            logger.info(
                "Threshold %d score: %.6f",
                current_threshold,
                score,
            )
            logger.debug(
                "Threshold %d samples: %s",
                current_threshold,
                ", ".join(f"{s:.6f}" for s in samples),
            )

            # Accept the first threshold within tolerance
            if score <= MAD_TOLERANCE:
                logger.info("Threshold %d with score %.6f is acceptable.", current_threshold, score)
                return current_threshold

            step = compute_step_increase(current_threshold, score)
            current_threshold += step
            logger.info("Next threshold %d (+%d)", current_threshold, step)

        return None  # No acceptable threshold found

    def _evaluate_threshold(self, model: CalibrationModel) -> tuple[float, list[float]]:
        old_model = self._probe.model
        try:
            self._probe.model = model
            samples: list[float] = []

            for _ in range(self._config.touch_samples * 3):
                pos = self._probe.perform_single_probe()
                if pos < SAFE_TRIGGER_MIN_HEIGHT:
                    msg = f"""
                        probe triggered at {pos:.3f}, far below expected bed level
                        Please ensure that z is homed to within {SAFE_TRIGGER_MIN_HEIGHT:.1f}mm of the bed.
                    """
                    raise RuntimeError(msg)
                samples.append(pos)

                if len(samples) >= 3:
                    current_score = self._evaluate_samples(samples)
                    # Early exit only for clearly unstable thresholds
                    if current_score > 5 * MAD_TOLERANCE:
                        return current_score, samples

            final_score = self._evaluate_samples(samples)
            return final_score, samples
        finally:
            self._probe.model = old_model

    def _evaluate_samples(self, samples: list[float]) -> float:
        return compute_mad(samples)
