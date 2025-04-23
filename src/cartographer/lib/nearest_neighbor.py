from __future__ import annotations

import logging
from typing import Generic, Protocol, TypeVar, final

import numpy as np

try:
    from scipy.spatial import KDTree

    kd_tree = KDTree
except ImportError:
    kd_tree = None


class Point(Protocol):
    x: float
    y: float


P = TypeVar("P", bound=Point, covariant=True)

MAX_CLUSTER_DISTANCE = 1.0

logger = logging.getLogger(__name__)


@final
class NearestNeighborSearcher(Generic[P]):
    tree: KDTree[None, None] | None = None

    def __init__(self, positions: list[P]) -> None:
        """Build a nearest neighbor searcher using the given positions."""
        self.positions = positions

        if kd_tree is not None:
            self.tree = kd_tree([(p.x, p.y) for p in positions])

    def query(self, point: Point) -> P | None:
        """Find the nearest point to the given point."""
        if self.tree is not None:
            _, index = self.tree.query((point.x, point.y), distance_upper_bound=MAX_CLUSTER_DISTANCE)  # pyright: ignore[reportUnknownMemberType]
            if index == self.tree.n:
                return None
        else:
            index = self._naive_query(point)
            if index is None:
                return None

        return self.positions[index]

    def _naive_query(self, point: Point) -> int | None:
        """Find the nearest point to the given point using a naive approach."""
        min_distance = MAX_CLUSTER_DISTANCE
        nearest_point: int | None = None
        for index, pos in enumerate(self.positions):
            dist = float(np.sqrt((point.x - pos.x) ** 2 + (point.y - pos.y) ** 2))
            if dist < min_distance:
                min_distance: float = dist
                nearest_point = index
        return nearest_point
