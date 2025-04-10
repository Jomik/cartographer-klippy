from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

import numpy as np
from typing_extensions import override

from cartographer.printer_interface import C, Macro, MacroParams, Probe, S

if TYPE_CHECKING:
    from cartographer.printer_interface import Toolhead
    from cartographer.probes.scan_probe import ScanProbe
    from cartographer.probes.touch_probe import TouchProbe

logger = logging.getLogger(__name__)


@final
class ProbeMacro(Macro[MacroParams]):
    name = "PROBE"
    description = "Probe the bed to get the height offset at the current position."
    last_distance: float = 0

    def __init__(self, probe: Probe) -> None:
        self._probe = probe

    @override
    def run(self, params: MacroParams) -> None:
        distance = self._probe.probe()
        logger.info("Result is z=%.6f", distance)
        self.last_distance = distance


@final
class ProbeAccuracyMacro(Macro[MacroParams]):
    name = "PROBE_ACCURACY"
    description = "Probe the bed multiple times to measure the accuracy of the probe."

    def __init__(self, probe: Probe, toolhead: Toolhead) -> None:
        self._probe = probe
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        lift_speed = params.get_float("LIFT_SPEED", 5.0, above=0)
        retract = params.get_float("SAMPLE_RETRACT_DIST", 1.0, minval=0)
        sample_count = params.get_int("SAMPLES", 10, minval=1)
        position = self._toolhead.get_position()

        logger.info(
            "PROBE_ACCURACY at X:%.3f Y:%.3f Z:%.3f (samples=%d retract=%.3f lift_speed=%.1f)",
            position.x,
            position.y,
            position.z,
            sample_count,
            retract,
            lift_speed,
        )

        self._toolhead.manual_move(z=position.z + retract, speed=lift_speed)
        measurements: list[float] = []
        while len(measurements) < sample_count:
            distance = self._probe.probe()
            measurements.append(distance)
            pos = self._toolhead.get_position()
            self._toolhead.manual_move(z=pos.z + retract, speed=lift_speed)
        logger.debug("Measurements gathered: %s", measurements)

        max_value = max(measurements)
        min_value = min(measurements)
        range_value = max_value - min_value
        avg_value = np.mean(measurements)
        median = np.median(measurements)
        std_dev = np.std(measurements)

        logger.info(
            """probe accuracy results: maximum %.6f, minimum %.6f, range %.6f, \
            average %.6f, median %.6f, standard deviation %.6f""",
            max_value,
            min_value,
            range_value,
            avg_value,
            median,
            std_dev,
        )


@final
class QueryProbeMacro(Macro[MacroParams]):
    name = "QUERY_PROBE"
    description = "Return the status of the z-probe"
    last_triggered: bool = False

    def __init__(self, probe: Probe, toolhead: Toolhead) -> None:
        self._probe = probe
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        time = self._toolhead.get_last_move_time()
        triggered = self._probe.query_is_triggered(time)
        logger.info("probe: %s", "TRIGGERED" if triggered else "open")
        self.last_triggered = triggered


@final
class ZOffsetApplyProbeMacro(Macro[MacroParams]):
    name = "Z_OFFSET_APPLY_PROBE"
    description = "Adjust the probe's z_offset"

    def __init__(self, toolhead: Toolhead, scan_probe: ScanProbe[C, S], touch_probe: TouchProbe[object]) -> None:
        self._toolhead = toolhead
        self._scan_probe = scan_probe
        self._touch_probe = touch_probe

    @override
    def run(self, params: MacroParams) -> None:
        additional_offset = self._toolhead.get_gcode_z_offset()
        # If a touch model is loaded, we assume the user uses touch.
        probe_mode, probe = (
            ("touch", self._touch_probe) if self._touch_probe.model is not None else ("scan", self._scan_probe)
        )
        current_offset = probe.offset.z
        if probe.model is None:
            msg = "no probe model loaded"
            raise RuntimeError(msg)

        new_offset = current_offset - additional_offset
        logger.info(
            """cartographer: %s %s z_offset: %.3f
            The SAVE_CONFIG command will update the printer config file
            with the above and restart the printer.""",
            probe_mode,
            probe.model.name,
            new_offset,
        )

        probe.save_z_offset(new_offset)
