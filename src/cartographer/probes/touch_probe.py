from __future__ import annotations

import logging
from typing import Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.printer_interface import C, Endstop, HomingState, Mcu, S, Toolhead

logger = logging.getLogger(__name__)


class Configuration(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def threshold(self) -> int: ...

    @property
    def speed(self) -> float: ...

    @property
    def z_offset(self) -> float: ...

    def save_z_offset(self, offset: float) -> None: ...

    @property
    def samples(self) -> int: ...

    def save_samples(self, samples: int) -> None: ...

    @property
    def retries(self) -> int: ...

    def save_retries(self, retries: int) -> None: ...


TOLERANCE = 0.008
RETRACT_DISTANCE = 2.0


@final
class TouchProbe(Endstop[C]):
    """Implementation for Survey Touch."""

    @property
    def z_offset(self) -> float:
        return self.config.z_offset

    def __init__(
        self,
        mcu: Mcu[C, S],
        toolhead: Toolhead,
        config: Configuration,
    ) -> None:
        self._toolhead = toolhead
        self._mcu = mcu
        self.config = config

    def probe(self, *, speed: float) -> float:
        if not self._toolhead.is_homed("z"):
            msg = "Z axis must be homed before probing"
            raise RuntimeError(msg)
        self._toolhead.manual_move(z=5, speed=speed)
        self._toolhead.wait_moves()
        tries = self.config.retries + 1
        for i in range(tries):
            try:
                return self._run_probe()
            except ValueError as err:
                logger.info("Touch attempt %d / %d failed: %s", i + 1, tries, err)

        msg = f"failed after {tries} attempts"
        raise RuntimeError(msg)

    def _run_probe(self) -> float:
        collected: list[float] = []
        for i in range(self.config.samples):
            logger.debug("Starting touch %d", i + 1)
            collected.append(self._probe_distance())
            if len(collected) < 3:
                continue  # Need at least 3 samples for meaningful statistics

            std_dev = np.std(collected, ddof=1)  # Sample standard deviation

            if std_dev > TOLERANCE:
                msg = f"standard deviation ({std_dev:.6f}) exceeded tolerance ({TOLERANCE:.6f})"
                raise ValueError(msg)

        mean_val = np.mean(collected)
        final_value = np.median(collected) if len(collected) == 3 else mean_val
        return float(final_value)

    def _probe_distance(self) -> float:
        self._toolhead.wait_moves()
        distance = self._toolhead.z_homing_move(self, bottom=-2.0, speed=self.config.speed)
        pos = self._toolhead.get_position()
        self._toolhead.manual_move(
            z=pos.z + RETRACT_DISTANCE,
            speed=self.config.speed,
        )
        return distance

    @override
    def query_is_triggered(self, print_time: float) -> bool:
        # Touch endstop is never in a triggered state.
        return False

    @override
    def get_endstop_position(self) -> float:
        return 0

    @override
    def home_start(self, print_time: float) -> C:
        if self.config.threshold <= 0:
            msg = "Threshold must be greater than 0"
            raise RuntimeError(msg)
        return self._mcu.start_homing_touch(print_time, self.config.threshold)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        if self not in homing_state.endstops:
            return
        if not homing_state.is_homing_z():
            return

        homing_state.set_z_homed_position(0)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu.stop_homing(home_end_time)
