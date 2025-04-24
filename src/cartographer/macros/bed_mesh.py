from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Protocol, final

import numpy as np
from typing_extensions import override

from cartographer.lib.nearest_neighbor import NearestNeighborSearcher
from cartographer.printer_interface import C, Macro, P, Position, S, Toolhead

if TYPE_CHECKING:
    from cartographer.interfaces import TaskExecutor
    from cartographer.probe.scan_mode import Model, ScanMode

logger = logging.getLogger(__name__)


class Configuration(Protocol):
    scan_speed: float
    scan_height: float
    scan_mesh_runs: int


@dataclass
class MeshPoint:
    x: float
    y: float
    include: bool


class MeshHelper(Generic[P], Protocol):
    def orig_macro(self, params: P) -> None: ...
    def prepare(self, params: P) -> None: ...
    def generate_path(self) -> list[MeshPoint]: ...
    def finalize(self, offset: Position, positions: list[Position]): ...


@final
class BedMeshCalibrateMacro(Macro[P]):
    name = "BED_MESH_CALIBRATE"
    description = "Gather samples across the bed to calibrate the bed mesh."

    def __init__(
        self,
        probe: ScanMode[C, S],
        toolhead: Toolhead,
        helper: MeshHelper[P],
        task_executor: TaskExecutor,
        config: Configuration,
    ) -> None:
        self.probe = probe
        self.toolhead = toolhead
        self.helper = helper
        self.task_executor = task_executor
        self.config = config

    @override
    def run(self, params: P) -> None:
        method = params.get("METHOD", default="scan").lower()
        if method != "scan" and method != "rapid_scan":
            return self.helper.orig_macro(params)

        runs = params.get_int("RUNS", default=self.config.scan_mesh_runs, minval=1)
        speed = params.get_float("SPEED", default=self.config.scan_speed, minval=1)
        scan_height = params.get_float("HORIZONTAL_MOVE_Z", default=self.config.scan_height, minval=1)
        if self.probe.model is None:
            msg = "cannot run bed mesh without a model"
            raise RuntimeError(msg)

        self.helper.prepare(params)

        self.toolhead.move(z=scan_height, speed=5)
        path = self.helper.generate_path()
        self._move_to_point(path[0], speed)

        with self.probe.start_session() as session:
            session.wait_for(lambda samples: len(samples) >= 5)
            for i in range(runs):
                is_odd = i & 1  # Bitwise check for odd numbers
                # Every other run should be going in reverse
                path_iter = reversed(path) if is_odd else path
                for point in path_iter:
                    self._move_to_point(point, speed)
                self.toolhead.dwell(0.250)
                self.toolhead.wait_moves()
            time = self.toolhead.get_last_move_time()
            session.wait_for(lambda samples: samples[-1].time >= time)
            count = len(session.items)
            session.wait_for(lambda samples: len(samples) >= count + 50)

        samples = session.get_items()
        logger.debug("Gathered %d samples", len(samples))

        positions = self.task_executor.run(self._calculate_positions, self.probe.model, path, samples, scan_height)

        self.helper.finalize(self.probe.offset, positions)

    def _move_to_point(self, point: MeshPoint, speed: float) -> None:
        offset = self.probe.offset
        self.toolhead.move(x=point.x - offset.x, y=point.y - offset.y, speed=speed)

    def _key(self, point: MeshPoint) -> tuple[float, float]:
        return round(point.x, 2), round(point.y, 2)

    def _calculate_positions(
        self, model: Model, path: list[MeshPoint], samples: list[S], scan_height: float
    ) -> list[Position]:
        included_points = [p for p in path if p.include]
        searcher = NearestNeighborSearcher(included_points)

        clusters = self._build_clusters(
            samples,
            included_points,
            searcher,
        )
        return [
            self._compute_position(
                (x, y),
                cluster,
                model,
                scan_height,
            )
            for (x, y), cluster in clusters.items()
        ]

    def _build_clusters(
        self,
        samples: list[S],
        points: list[MeshPoint],
        searcher: NearestNeighborSearcher[MeshPoint],
    ) -> dict[tuple[float, float], list[S]]:
        offset = self.probe.offset

        def classify_sample(s: S) -> tuple[tuple[float, float], S] | None:
            if s.position is None:
                return None
            adjusted = MeshPoint(s.position.x + offset.x, s.position.y + offset.y, include=True)
            point = searcher.query(adjusted)
            if point is None or not point.include:
                return None
            return self._key(point), s

        cluster_map: dict[tuple[float, float], list[S]] = {self._key(p): [] for p in points}
        for result in map(classify_sample, samples):
            if result is not None:
                key, sample = result
                cluster_map[key].append(sample)
        return cluster_map

    def _compute_position(
        self,
        key: tuple[float, float],
        cluster: list[S],
        model: Model,
        scan_height: float,
    ) -> Position:
        offset = self.probe.offset
        x, y = key
        if not cluster:
            msg = f"cluster ({x:.2f},{y:.2f}) has no samples"
            raise RuntimeError(msg)

        distances = list(map(lambda s: model.frequency_to_distance(s.frequency), cluster))
        median_distance = float(np.median(distances))

        if not math.isfinite(median_distance):
            msg = f"cluster ({x:.2f},{y:.2f}) has no valid samples"
            raise RuntimeError(msg)

        trigger_z = scan_height + self.probe.probe_height - median_distance
        pos = Position(x - offset.x, y - offset.y, trigger_z)
        return self.toolhead.apply_axis_twist_compensation(pos)
