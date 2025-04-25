from __future__ import annotations

import logging
from math import floor, sqrt
from typing import Generic, Protocol, TypeVar, final

logger = logging.getLogger(__name__)

MAX_CLUSTER_DISTANCE = 1.0
CELL_SIZE = 0.5  # must be ≤ MAX_CLUSTER_DISTANCE for full coverage


class Point(Protocol):
    x: float
    y: float


P = TypeVar("P", bound=Point, covariant=True)


@final
class NearestNeighborSearcher(Generic[P]):
    def __init__(self, points: list[P]) -> None:
        self.points = points
        self.grid: dict[tuple[int, int], list[P]] = {}
        for point in points:
            cell = self._cell_key(point.x, point.y)
            self.grid.setdefault(cell, []).append(point)

    def batch_query(self, positions: list[tuple[float, float]]) -> list[P | None]:
        results: list[P | None] = []

        for px, py in positions:
            best = None
            best_dist = MAX_CLUSTER_DISTANCE

            cx, cy = self._cell_key(px, py)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cell = (cx + dx, cy + dy)
                    for p in self.grid.get(cell, []):
                        dist = sqrt((px - p.x) ** 2 + (py - p.y) ** 2)
                        if dist < best_dist:
                            best_dist = dist
                            best = p
            results.append(best)

        return results

    def _cell_key(self, x: float, y: float) -> tuple[int, int]:
        return (floor(x / CELL_SIZE), floor(y / CELL_SIZE))
