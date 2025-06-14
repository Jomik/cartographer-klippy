from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeVar, final

import numpy as np
from typing_extensions import override

from cartographer.interfaces.printer import Macro, MacroParams, Position, Sample, SupportsFallbackMacro, Toolhead
from cartographer.lib.log import log_duration
from cartographer.macros.bed_mesh.mesh_utils import assign_samples_to_grid
from cartographer.macros.bed_mesh.serpentine_path import SerpentinePathPlanner
from cartographer.macros.utils import get_choice

if TYPE_CHECKING:
    from cartographer.interfaces.configuration import Configuration
    from cartographer.interfaces.multiprocessing import TaskExecutor
    from cartographer.macros.bed_mesh.interfaces import BedMeshAdapter, Point
    from cartographer.probe import Probe

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BedMeshCalibrateConfiguration:
    mesh_min: tuple[float, float]
    mesh_max: tuple[float, float]
    travel_speed: float
    zero_reference_position: Point

    @staticmethod
    def from_config(config: Configuration):
        return BedMeshCalibrateConfiguration(
            mesh_min=config.bed_mesh.mesh_min,
            mesh_max=config.bed_mesh.mesh_max,
            travel_speed=config.general.travel_speed,
            zero_reference_position=config.bed_mesh.zero_reference_position,
        )


_directions: list[Literal["x", "y"]] = ["x", "y"]
MINIMUM_SAMPLE_COUNT = 3
WARNING_SAMPLE_COUNT = 5


@final
class BedMeshCalibrateMacro(Macro, SupportsFallbackMacro):
    name = "BED_MESH_CALIBRATE"
    description = "Gather samples across the bed to calibrate the bed mesh."

    _fallback: Macro | None = None

    def __init__(
        self,
        probe: Probe,
        toolhead: Toolhead,
        adapter: BedMeshAdapter,
        task_executor: TaskExecutor,
        config: BedMeshCalibrateConfiguration,
    ) -> None:
        self.probe = probe
        self.toolhead = toolhead
        self.adapter = adapter
        self.task_executor = task_executor
        self.config = config

    @override
    def set_fallback_macro(self, macro: Macro) -> None:
        self._fallback = macro

    @override
    def run(self, params: MacroParams) -> None:
        method = params.get("METHOD", "scan")
        if method.lower() != "scan":
            if self._fallback is None:
                msg = f"Bed mesh calibration method '{method}' not supported"
                raise RuntimeError(msg)
            return self._fallback.run(params)

        profile = params.get("PROFILE", "default")
        speed = params.get_float("SPEED", default=self.config.travel_speed, minval=50)
        passes = params.get_int("PASSES", default=1, minval=1)
        height = params.get_float("HEIGHT", default=4.0, minval=0.5, maxval=5)
        direction: Literal["x", "y"] = get_choice(params, "DIRECTION", _directions, default="x")
        mesh_points = self._generate_mesh_points()
        snake = SerpentinePathPlanner(direction)
        path = list(snake.generate_path(mesh_points))

        samples = self._sample_path(path, passes=passes, height=height, speed=speed)
        positions = self.task_executor.run(self._calculate_positions, mesh_points, samples, height)

        self.adapter.apply_mesh(positions, profile)

    def _generate_mesh_points(self) -> list[Point]:
        x_min, y_min = self.config.mesh_min
        x_max, y_max = self.config.mesh_max
        x_res, y_res = 10, 10

        x_points = np.linspace(x_min, x_max, x_res)
        y_points = np.linspace(y_min, y_max, y_res)

        mesh = [(x, y) for x in x_points for y in y_points]  # shape: [y][x]
        return mesh

    @log_duration("Bed scan")
    def _sample_path(self, path: list[Point], *, speed: float, height: float, passes: int) -> list[Sample]:
        self.toolhead.move(z=height, speed=5)
        self._move_probe_to_point(path[0], speed)
        self.toolhead.wait_moves()

        with self.probe.scan.start_session() as session:
            session.wait_for(lambda samples: len(samples) >= 10)
            for i in range(passes):
                for point in path if i % 2 == 0 else reversed(path):
                    self._move_probe_to_point(point, speed)
                self.toolhead.dwell(0.250)
                self.toolhead.wait_moves()
            move_time = self.toolhead.get_last_move_time()
            session.wait_for(lambda samples: samples[-1].time >= move_time)
            count = len(session.items)
            session.wait_for(lambda samples: len(samples) >= count + 10)

        samples = session.get_items()
        logger.debug("Gathered %d samples", len(samples))
        return samples

    def _probe_point_to_nozzle_point(self, point: Point) -> Point:
        x, y = point
        offset = self.probe.scan.offset
        return (x - offset.x, y - offset.y)

    def _nozzle_point_to_probe_point(self, point: Point) -> Point:
        x, y = point
        offset = self.probe.scan.offset
        return (x + offset.x, y + offset.y)

    def _move_probe_to_point(self, point: Point, speed: float) -> None:
        x, y = self._probe_point_to_nozzle_point(point)
        self.toolhead.move(x=x, y=y, speed=speed)

    @log_duration("Cluster position computation")
    def _calculate_positions(self, mesh_points: list[Point], samples: list[Sample], height: float) -> list[Position]:
        nozzle_mesh_points = [self._probe_point_to_nozzle_point(point) for point in mesh_points]
        results = assign_samples_to_grid(nozzle_mesh_points, samples, self.probe.scan.calculate_sample_distance)

        probe_positions: list[Position] = []
        for result in results:
            x, y = result.point
            if not math.isfinite(result.z):
                msg = f"Cluster ({x:.2f},{y:.2f}) has no valid samples"
                raise RuntimeError(msg)

            if result.sample_count < MINIMUM_SAMPLE_COUNT:
                msg = f"Cluster ({x:.2f},{y:.2f}) has less than {MINIMUM_SAMPLE_COUNT} samples, slow down"
                raise RuntimeError(msg)

            if result.sample_count < WARNING_SAMPLE_COUNT:
                logger.warning("Cluster (%.2f,%.2f) has only %d samples", x, y, result.sample_count)

            trigger_z = height - result.z
            nozzle_position = self.toolhead.apply_axis_twist_compensation(Position(x=x, y=y, z=trigger_z))
            px, py = self._nozzle_point_to_probe_point(result.point)
            probe_positions.append(Position(x=px, y=py, z=nozzle_position.z))

        return probe_positions


T = TypeVar("T")


def flatten(xss: list[list[T]]) -> list[T]:
    return [x for xs in xss for x in xs]
