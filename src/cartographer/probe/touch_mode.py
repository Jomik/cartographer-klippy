from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING, Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.lib.statistics import compute_mad
from cartographer.printer_interface import C, Endstop, HomingState, Mcu, Position, ProbeMode, S, Toolhead

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cartographer.configuration import TouchModelConfiguration

logger = logging.getLogger(__name__)


STD_TOLERANCE = 0.008
RETRACT_DISTANCE = 2.0
MAX_TOUCH_TEMPERATURE = 155


class Configuration(Protocol):
    move_speed: float

    touch_samples: int
    touch_max_samples: int

    x_offset: float
    y_offset: float
    mesh_min: tuple[float, float]
    mesh_max: tuple[float, float]


class TouchError(RuntimeError):
    pass


@dataclass(frozen=True)
class TouchBoundaries:
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def is_within(self, *, x: float, y: float) -> bool:
        epsilon = 0.01
        in_x_bounds = (self.min_x - epsilon) <= x <= (self.max_x + epsilon)
        in_y_bounds = (self.min_y - epsilon) <= y <= (self.max_y + epsilon)
        return in_x_bounds and in_y_bounds

    @staticmethod
    def from_config(config: Configuration) -> TouchBoundaries:
        mesh_min_x, mesh_min_y = config.mesh_min
        mesh_max_x, mesh_max_y = config.mesh_max
        x_offset = config.x_offset
        y_offset = config.y_offset

        # For negative offsets: increase min bounds, leave max bounds unchanged
        min_x = mesh_min_x - min(x_offset, 0)  # Only subtract negative offsets
        min_y = mesh_min_y - min(y_offset, 0)  # Only subtract negative offsets
        # For positive offsets: reduce max bounds, leave min bounds unchanged
        max_x = mesh_max_x - max(x_offset, 0)  # Only subtract positive offsets
        max_y = mesh_max_y - max(y_offset, 0)  # Only subtract positive offsets

        return TouchBoundaries(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
        )


@final
class TouchMode(ProbeMode, Endstop[C]):
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
        return Position(0.0, 0.0, z_offset)

    @override
    def save_z_offset(self, new_offset: float) -> None:
        self.get_model().save_z_offset(new_offset)

    @property
    @override
    def is_ready(self) -> bool:
        return self.model is not None

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

        self.boundaries = TouchBoundaries.from_config(config)

    @override
    def perform_probe(self) -> float:
        if not self._toolhead.is_homed("z"):
            msg = "z axis must be homed before probing"
            raise RuntimeError(msg)

        if self._toolhead.get_position().z < 5:
            self._toolhead.move(z=5, speed=self.config.move_speed)
        self._toolhead.wait_moves()

        return self._run_probe()

    def _run_probe(self) -> float:
        collected: list[float] = []
        touch_samples = self.config.touch_samples
        touch_max_samples = self.config.touch_max_samples
        logger.debug("Starting touch sequence for %d samples within %d touches...", touch_samples, touch_max_samples)

        for i in range(touch_max_samples):
            trigger_pos = self.perform_single_probe()
            collected.append(trigger_pos)
            logger.debug("Touch %d: %.6f", i + 1, trigger_pos)

            if len(collected) < touch_samples:
                continue

            valid_combo = self._find_valid_combination(collected, touch_samples)
            if valid_combo is None:
                continue

            self._log_sample_stats("Acceptable touch combination found", valid_combo)

            return float(np.median(valid_combo) if len(valid_combo) > 3 else np.mean(valid_combo))

        self._log_sample_stats("No valid touch combination found in samples", collected)
        msg = f"unable to find {touch_samples} samples within tolerance after {touch_max_samples} touches"
        raise TouchError(msg)

    def _find_valid_combination(self, samples: list[float], size: int) -> tuple[float, ...] | None:
        for combo in combinations(samples, size):
            if np.std(combo) <= STD_TOLERANCE:
                return combo
        return None

    def perform_single_probe(self) -> float:
        model = self.get_model()
        if self._toolhead.get_position().z < RETRACT_DISTANCE:
            self._toolhead.move(z=RETRACT_DISTANCE, speed=self.config.move_speed)
        self._toolhead.wait_moves()
        trigger_pos = self._toolhead.z_homing_move(self, bottom=-2.0, speed=model.speed)
        pos = self._toolhead.get_position()
        self._toolhead.move(
            z=max(pos.z + RETRACT_DISTANCE, RETRACT_DISTANCE),
            speed=self.config.move_speed,
        )
        return trigger_pos

    @override
    def home_start(self, print_time: float) -> C:
        model = self.get_model()
        if model.threshold <= 0:
            msg = "threshold must be greater than 0"
            raise RuntimeError(msg)

        pos = self._toolhead.get_position()
        if not self.is_within_boundaries(x=pos.x, y=pos.y):
            msg = f"position ({pos.x:.2f},{pos.y:.2f}) is outside of the touch boundaries"
            raise RuntimeError(msg)

        nozzle = self._toolhead.get_extruder_temperature()
        if nozzle.current > MAX_TOUCH_TEMPERATURE or nozzle.target > MAX_TOUCH_TEMPERATURE:
            msg = f"nozzle temperature must be below {MAX_TOUCH_TEMPERATURE - 5:d}C"
            raise RuntimeError(msg)
        return self._mcu.start_homing_touch(print_time, model.threshold)

    def is_within_boundaries(self, *, x: float, y: float) -> bool:
        return self.boundaries.is_within(x=x, y=y)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        if self not in homing_state.endstops:
            return
        if not homing_state.is_homing_z():
            return

        homing_state.set_z_homed_position(self.get_model().z_offset)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu.stop_homing(home_end_time)

    @override
    def query_is_triggered(self, print_time: float) -> bool:
        # Touch endstop is never in a triggered state.
        return False

    @override
    def get_endstop_position(self) -> float:
        return self.offset.z

    def _log_sample_stats(self, message: str, samples: Sequence[float]) -> None:
        max_v, min_v = max(samples), min(samples)
        mean = np.mean(samples)
        median = np.median(samples)
        range_v = max_v - min_v
        std_dev = np.std(samples)
        mad = compute_mad(samples)
        logger.debug(
            """
                %s: (%s)
                maximum %.6f, minimum %.6f, range %.6f,
                average %.6f, median %.6f, standard deviation %.6f,
                median absolute deviation %.6f
                """,
            message,
            ", ".join(f"{s:.6f}" for s in samples),
            max_v,
            min_v,
            range_v,
            mean,
            median,
            std_dev,
            mad,
        )
