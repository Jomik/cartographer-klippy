from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.printer_interface import C, Endstop, HomingState, Mcu, Position, Probe, S, Toolhead

if TYPE_CHECKING:
    from cartographer.configuration import TouchModelConfiguration

logger = logging.getLogger(__name__)


TOLERANCE = 0.008
RETRACT_DISTANCE = 2.0


class Configuration(Protocol):
    x_offset: float
    y_offset: float
    move_speed: float

    touch_retries: int
    touch_samples: int


@final
class TouchProbe(Probe, Endstop[C]):
    """Implementation for Survey Touch."""

    def get_model(self) -> TouchModelConfiguration:
        if self.model is None:
            msg = "no touch model loaded"
            raise RuntimeError(msg)
        return self.model

    @property
    @override
    def offset(self) -> Position:
        z_offset = self.model.z_offset if self.model else 0.0
        return Position(self.config.x_offset, self.config.y_offset, z_offset)

    def __init__(
        self,
        mcu: Mcu[C, S],
        toolhead: Toolhead,
        config: Configuration,
        *,
        model: TouchModelConfiguration | None,
    ) -> None:
        self._toolhead = toolhead
        self._mcu = mcu
        self.config = config
        self.model = model

    @override
    def probe(self) -> float:
        if not self._toolhead.is_homed("z"):
            msg = "Z axis must be homed before probing"
            raise RuntimeError(msg)
        self._toolhead.manual_move(z=5, speed=self.config.move_speed)
        self._toolhead.wait_moves()
        tries = self.config.touch_retries + 1
        for i in range(tries):
            try:
                return self._run_probe()
            except ValueError as err:
                logger.info("Touch attempt %d / %d failed: %s", i + 1, tries, err)

        msg = f"failed after {tries} attempts"
        raise RuntimeError(msg)

    def _run_probe(self) -> float:
        collected: list[float] = []
        for i in range(self.config.touch_samples):
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
        model = self.get_model()
        self._toolhead.wait_moves()
        distance = self._toolhead.z_homing_move(self, bottom=-2.0, speed=model.speed)
        pos = self._toolhead.get_position()
        self._toolhead.manual_move(
            z=pos.z + RETRACT_DISTANCE,
            speed=model.speed,
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
        model = self.get_model()
        if model.threshold <= 0:
            msg = "threshold must be greater than 0"
            raise RuntimeError(msg)
        return self._mcu.start_homing_touch(print_time, model.threshold)

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
