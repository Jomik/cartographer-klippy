from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Literal, final

import numpy as np
from typing_extensions import override

from cartographer.interfaces.printer import Macro, MacroParams, Position, Sample, SupportsFallbackMacro, Toolhead
from cartographer.lib.log import log_duration
from cartographer.macros.bed_mesh.alternating_snake import AlternatingSnakePathGenerator
from cartographer.macros.bed_mesh.mesh_utils import assign_samples_to_grid
from cartographer.macros.bed_mesh.snake_path import SnakePathGenerator
from cartographer.macros.bed_mesh.spiral_path import SpiralPathGenerator
from cartographer.macros.utils import get_choice, get_float_tuple, get_int_tuple

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
    probe_count: tuple[int, int]
    speed: float
    adaptive_margin: float
    zero_reference_position: Point

    runs: int
    direction: Literal["x", "y"]
    height: float
    corner_radius: float
    path: Literal["snake", "alternating_snake", "spiral"]

    @staticmethod
    def from_config(config: Configuration):
        return BedMeshCalibrateConfiguration(
            mesh_min=config.bed_mesh.mesh_min,
            mesh_max=config.bed_mesh.mesh_max,
            probe_count=config.bed_mesh.probe_count,
            speed=config.bed_mesh.speed,
            adaptive_margin=config.bed_mesh.adaptive_margin,
            zero_reference_position=config.bed_mesh.zero_reference_position,
            runs=config.scan.mesh_runs,
            direction=config.scan.mesh_direction,
            height=config.scan.mesh_height,
            corner_radius=config.scan.mesh_corner_radius,
            path=config.scan.mesh_path,
        )


_directions: list[Literal["x", "y"]] = ["x", "y"]


class PathStrategy(ABC):
    @abstractmethod
    def __init__(self, main_direction: Literal["x", "y"] = "x", corner_radius: float = 5.0) -> None: ...
    @abstractmethod
    def generate_path(self, mesh_points: list[Point]) -> list[Point]: ...


PATH_STRATEGY_MAP = {
    "snake": SnakePathGenerator,
    "alternating_snake": AlternatingSnakePathGenerator,
    "spiral": SpiralPathGenerator,
}


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

        speed = params.get_float("SPEED", default=self.config.speed, minval=50)
        runs = params.get_int("RUNS", default=self.config.runs, minval=1)
        height = params.get_float("HEIGHT", default=self.config.height, minval=0.5, maxval=5)
        corner_radius = params.get_float("CORNER_RADIUS", default=self.config.corner_radius, minval=0)
        direction: Literal["x", "y"] = get_choice(params, "DIRECTION", _directions, default=self.config.direction)
        path_strategy_type = get_choice(params, "PATH", default=self.config.path, choices=PATH_STRATEGY_MAP.keys())
        path_strategy = PATH_STRATEGY_MAP[path_strategy_type](direction, corner_radius)

        adaptive = params.get_int("ADAPTIVE", default=0) != 0
        probe_count = get_int_tuple(params, "PROBE_COUNT", default=self.config.probe_count)

        mesh_min, mesh_max = self._calculate_mesh_bounds(params, adaptive)
        mesh_points = self._generate_mesh_points(mesh_min, mesh_max, probe_count)
        path = list(path_strategy.generate_path(mesh_points))

        samples = self._sample_path(path, runs=runs, height=height, speed=speed)
        positions = self.task_executor.run(self._calculate_positions, mesh_points, samples, height)

        profile = params.get("PROFILE", default="default" if not adaptive else None)
        self.adapter.apply_mesh(positions, profile)

    def _calculate_mesh_bounds(self, params: MacroParams, adaptive: bool) -> tuple[Point, Point]:
        mesh_min = get_float_tuple(params, "MESH_MIN", default=self.config.mesh_min)
        mesh_max = get_float_tuple(params, "MESH_MAX", default=self.config.mesh_max)
        margin = params.get_float("ADAPTIVE_MARGIN", self.config.adaptive_margin, minval=0)

        if not adaptive:
            return mesh_min, mesh_max

        points = list(chain.from_iterable(self.adapter.get_objects()))
        if not points:
            return mesh_min, mesh_max

        xs: tuple[float, ...]
        ys: tuple[float, ...]
        xs, ys = zip(*points)

        obj_min_x = max(min(xs) - margin, mesh_min[0])
        obj_max_x = min(max(xs) + margin, mesh_max[0])
        obj_min_y = max(min(ys) - margin, mesh_min[1])
        obj_max_y = min(max(ys) + margin, mesh_max[1])

        return (obj_min_x, obj_min_y), (obj_max_x, obj_max_y)

    def _generate_mesh_points(
        self, mesh_min: tuple[float, float], mesh_max: tuple[float, float], probe_count: tuple[int, int]
    ) -> list[Point]:
        x_min, y_min = mesh_min
        x_max, y_max = mesh_max
        x_res, y_res = probe_count

        x_points = np.linspace(x_min, x_max, x_res)
        y_points = np.linspace(y_min, y_max, y_res)

        mesh = [(x, y) for x in x_points for y in y_points]  # shape: [y][x]
        return mesh

    @log_duration("Bed scan")
    def _sample_path(self, path: list[Point], *, speed: float, height: float, runs: int) -> list[Sample]:
        self.toolhead.move(z=height, speed=5)
        self._move_probe_to_point(path[0], speed)
        self.toolhead.wait_moves()

        with self.probe.scan.start_session() as session:
            session.wait_for(lambda samples: len(samples) >= 10)
            for i in range(runs):
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

            trigger_z = height - result.z
            nozzle_position = self.toolhead.apply_axis_twist_compensation(Position(x=x, y=y, z=trigger_z))
            px, py = self._nozzle_point_to_probe_point(result.point)
            probe_positions.append(Position(x=px, y=py, z=nozzle_position.z))

        return probe_positions
