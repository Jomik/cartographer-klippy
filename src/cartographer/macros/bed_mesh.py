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
    from cartographer.probe.scan_mode import Model, ScanMode

logger = logging.getLogger(__name__)


class Configuration(Protocol):
    speed: float
    scan_height: float
    runs: int


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
        config: Configuration,
    ) -> None:
        self.probe = probe
        self.toolhead = toolhead
        self.helper = helper
        self.config = config

    @override
    def run(self, params: P) -> None:
        method = params.get("METHOD", default="scan").lower()
        if method != "scan" and method != "rapid_scan":
            return self.helper.orig_macro(params)

        runs = params.get_int("RUNS", default=self.config.runs, minval=1)
        speed = params.get_float("SPEED", default=self.config.speed, minval=1)
        scan_height = params.get_float("HEIGHT", default=self.config.scan_height, minval=1)
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
        positions = self._calculate_positions(self.probe.model, path, samples)

        self.helper.finalize(self.probe.offset, positions)

    def _move_to_point(self, point: MeshPoint, speed: float) -> None:
        offset = self.probe.offset
        self.toolhead.move(x=point.x - offset.x, y=point.y - offset.y, speed=speed)

    def _key(self, point: MeshPoint) -> tuple[float, float]:
        return round(point.x, 2), round(point.y, 2)

    def _calculate_positions(self, model: Model, path: list[MeshPoint], samples: list[S]) -> list[Position]:
        offset = self.probe.offset
        searcher = NearestNeighborSearcher(path)

        clusters: dict[tuple[float, float], list[S]] = {self._key(point): [] for point in path if point.include}

        for s in samples:
            position = self.toolhead.get_requested_position(s.time)
            point = searcher.query(Position(position.x + offset.x, position.y + offset.y, 0))
            if not point.include:
                continue
            clusters[self._key(point)].append(s)

        positions: list[Position] = []
        for (x, y), cluster in clusters.items():
            if len(cluster) == 0:
                msg = f"cluster ({x:.2f},{y:.2f}) has no samples"
                raise RuntimeError(msg)

            dist = float(np.median([model.frequency_to_distance(s.frequency) for s in cluster]))
            if not math.isfinite(dist):
                msg = f"cluster ({x:.2f},{y:.2f}) has no valid samples"
                raise RuntimeError(msg)
            positions.append(Position(x, y, self.probe.probe_height - dist))

        return positions
