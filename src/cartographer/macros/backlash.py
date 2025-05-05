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
        delta = 0.2  # Smaller delta is better for detecting subtle backlash

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

        global_mean = np.mean(samples["up"] + samples["down"])
        mean_up = np.mean(samples["up"]) - global_mean
        mean_down = np.mean(samples["down"]) - global_mean
        std_up = np.std(samples["up"])
        std_down = np.std(samples["down"])
        backlash = mean_down - mean_up  # Positive = down sits lower than up

        logger.info(
            """
            Backlash estimation results (normalized) over %d iterations:
            Mean up: %.5f mm
            Mean down: %.5f mm
            Std dev up: %.5f mm
            Std dev down: %.5f mm
            Estimated backlash (down - up): %.5f mm
            """,
            iterations,
            mean_up,
            mean_down,
            std_up,
            std_down,
            backlash,
        )
