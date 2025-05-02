import logging
from typing import Literal, final

import numpy as np
from typing_extensions import override

from cartographer.printer_interface import Macro, MacroParams, S, Toolhead
from cartographer.probe.scan_mode import ScanMode

logger = logging.getLogger(__name__)


@final
class EstimateBacklashMacro(Macro[MacroParams]):
    name = "ESTIMATE_BACKLASH"
    description = "Do a series of moves to estimate backlash on the Z axis."

    def __init__(self, toolhead: Toolhead, scan: ScanMode[object, S]) -> None:
        self._scan = scan
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        iterations = params.get_int("ITERATIONS", 10, minval=1)
        speed = 5
        height = 2
        delta = 1

        # TODO: Maybe this should be a probing move?
        self._toolhead.move(z=height, speed=speed)
        samples: dict[Literal["up", "down"], list[float]] = {"up": [], "down": []}

        with self._scan.start_session():
            for _ in range(iterations):
                for direction in samples:
                    dir = 1 if direction == "up" else -1
                    self._toolhead.move(z=height + delta * dir, speed=speed)
                    self._toolhead.move(z=height, speed=speed)
                    self._toolhead.wait_moves()
                    dist = self._scan.measure_distance()
                    samples[direction].append(dist)

        logger.debug("Samples up: %s", samples["up"])
        logger.debug("Samples down: %s", samples["down"])

        mean_up = np.mean(samples["up"])
        mean_down = np.mean(samples["down"])
        median_up = np.median(samples["up"]) - mean_up
        median_down = np.median(samples["down"]) - mean_down
        std_up = np.std(samples["up"])
        std_down = np.std(samples["down"])

        logger.info(
            """
            Backlash estimation results over %d iterations:
            Median up: %.3f
            Median down: %.3f
            Standard deviation up: %.3f
            Standard deviation down: %.3f
            Delta: %.3f
            """,
            iterations,
            median_up,
            median_down,
            std_up,
            std_down,
            median_down - median_up,
        )
