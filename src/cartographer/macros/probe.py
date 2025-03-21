from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

import numpy as np
from typing_extensions import override

from cartographer.macros.interface import Macro, MacroParams

if TYPE_CHECKING:
    from cartographer.endstops.scan_endstop import ScanEndstop
    from cartographer.printer import Toolhead
    from cartographer.probes.scan_probe import S, ScanProbe

logger = logging.getLogger(__name__)


@final
class ProbeMacro(Macro):
    name = "PROBE"
    description = "Probe the bed to get the height offset at the current position."

    def __init__(self, scan_probe: ScanProbe[S]) -> None:
        self._scan_probe = scan_probe

    @override
    def run(self, params: MacroParams) -> None:
        speed = params.get_float("speed", 3.0, above=0)

        distance = self._scan_probe.probe(speed=speed)
        logger.info("Result is z=%.6f", distance)
        # TODO: Update status object


@final
class ProbeAccuracyMacro(Macro):
    name = "PROBE_ACCURACY"
    description = "Probe the bed multiple times to measure the accuracy of the probe."

    def __init__(self, scan_probe: ScanProbe[S], toolhead: Toolhead) -> None:
        self._scan_probe = scan_probe
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        speed = params.get_float("speed", 3.0, above=0)
        sample_count = params.get_int("samples", 10, minval=1)

        probe_height = self._scan_probe.probe_height

        self._toolhead.manual_move(z=probe_height, speed=speed)
        measurements: list[float] = []
        while len(measurements) < sample_count:
            distance = self._scan_probe.probe(speed=speed)
            measurements.append(distance)
        max_value = max(measurements)
        min_value = min(measurements)
        range_value = max_value - min_value
        avg_value = np.mean(measurements)
        median = np.median(measurements)
        std_dev = np.std(measurements)

        logger.info(
            """probe accuracy results: maximum %.6f, minimum %.6f, range %.6f,
            average %.6f, median %.6f, standard deviation %.6f""",
            max_value,
            min_value,
            range_value,
            avg_value,
            median,
            std_dev,
        )


@final
class QueryProbe(Macro):
    name = "QUERY_PROBE"
    description = "Return the status of the z-probe"

    def __init__(self, scan_endstop: ScanEndstop[object], toolhead: Toolhead) -> None:
        self._scan_endstop = scan_endstop
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        time = self._toolhead.get_last_move_time()
        triggered = self._scan_endstop.query_is_triggered(time)
        logger.info("probe: %s", "TRIGGERED" if triggered else "open")


@final
class ZOffsetApplyProbe(Macro):
    name = "Z_OFFSET_APPLY_PROBE"
    description = "Adjust the probe's z_offset"

    def __init__(self, toolhead: Toolhead) -> None:
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        offset = self._toolhead.get_gcode_z_offset()
        # TODO: Get current offset from config
        current_offset = 0
        new_offset = current_offset - offset
        logger.info(
            """cartographer: z_offset: %.3f
            The SAVE_CONFIG command will update the printer config file
            with the above and restart the printer.""",
            new_offset,
        )
        # TODO: Save to config
