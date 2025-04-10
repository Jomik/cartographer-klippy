from __future__ import annotations

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


@final
class NearestNeighborSearcher(Generic[P]):
    tree: KDTree[None, None] | None = None

    def __init__(self, positions: list[P]) -> None:
        """Build a nearest neighbor searcher using the given positions."""
        self.positions = positions

        if kd_tree is not None:
            self.tree = kd_tree([(p.x, p.y) for p in positions])

    def query(self, point: Point) -> P:
        """Find the nearest point to the given point."""
        if self.tree is not None:
            _, index = self.tree.query((point.x, point.y))  # pyright: ignore[reportUnknownMemberType]
        else:
            index = self._naive_query(point)

        return self.positions[index]

    def _naive_query(self, point: Point) -> int:
        """Find the nearest point to the given point using a naive approach."""
        min_distance = float("inf")
        nearest_point = None
        for index, pos in enumerate(self.positions):
            dist: float = np.sqrt((point.x - pos.x) ** 2 + (point.y - pos.y) ** 2)
            if dist < min_distance:
                min_distance: float = dist
                nearest_point = index
        if nearest_point is None:
            msg = "no points to search for nearest neighbor."
            raise ValueError(msg)
        return nearest_point
