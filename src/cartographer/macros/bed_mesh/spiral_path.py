from __future__ import annotations

import math
from typing import TYPE_CHECKING, Iterator, final

import numpy as np

from cartographer.macros.bed_mesh.mesh_utils import cluster_points
from cartographer.macros.bed_mesh.pathing_utils import Vec, angle_deg, arc_points, normalize, perpendicular

if TYPE_CHECKING:
    from cartographer.macros.bed_mesh.interfaces import Point


@final
class SpiralPathPlanner:
    def __init__(self, corner_radius: float = 5.0):
        self.corner_radius = corner_radius

    def generate_path(self, points: list[Point]) -> Iterator[Point]:
        grid = cluster_points(points, "x")
        """Generate points in a spiral pattern from outer layers inward"""
        offset = 0

        # TODO: Remove unnecessary lines and corners

        while offset < math.floor(len(grid) / 2) and offset < math.floor(len(grid[0]) / 2):
            yield from grid[offset][offset : -offset - 1]

            yield from corner(grid[offset][-offset - 1], (1, 0), self.corner_radius)
            for i in range(offset + 1, len(grid) - offset):
                yield grid[i][-offset - 1]

            yield from corner(grid[-offset - 1][-offset - 1], (0, 1), self.corner_radius)
            yield from grid[-offset - 1][-offset - 2 : offset : -1]
            for i in range(len(grid) - offset - 1, offset, -1):
                yield grid[i][offset]

            offset += 1


def corner(point: Point, entry_dir: tuple[float, float], radius: float) -> Iterator[Point]:
    p1: Vec = np.array(point, dtype=float)
    direction: Vec = np.array(entry_dir, dtype=float)
    turn_ccw = True
    turn_angle = 90

    entry_perp = perpendicular(direction, ccw=turn_ccw)
    between = normalize(entry_perp - direction)
    start_angle = angle_deg(-between) - turn_angle / 2

    offset = between * radius
    yield from arc_points(p1 + offset, radius, start_angle, turn_angle)
