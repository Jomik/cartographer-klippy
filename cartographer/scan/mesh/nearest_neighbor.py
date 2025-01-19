from __future__ import annotations

from typing import List, Tuple, TypeVar, Dict
import numpy as np

try:
    from scipy.spatial import cKDTree  # pyright: ignore[reportMissingTypeStubs]

    kdTree = cKDTree
except ImportError:
    kdTree = None

T = TypeVar("T")


def cluster_points(
    positions: List[Tuple[float, float]], samples: List[Tuple[Tuple[float, float], T]]
) -> Dict[Tuple[float, float], List[T]]:
    clusters: Dict[Tuple[float, float], List[T]] = {pos: [] for pos in positions}
    if kdTree is not None:
        # Use the scipy implementation
        tree = kdTree(positions)
        for sample_pos, sample_value in samples:
            res: Tuple[float, int] = tree.query(sample_pos)
            _, index = res
            nearest_position = positions[index]
            clusters[nearest_position].append(sample_value)
        return clusters
    else:
        # Use the naive implementation
        for sample_pos, sample_value in samples:
            min_distance = float("inf")
            nearest_position = None
            for pos in positions:
                dist: float = np.sqrt(
                    (sample_pos[0] - pos[0]) ** 2 + (sample_pos[1] - pos[1]) ** 2
                )
                if dist < min_distance:
                    min_distance: float = dist
                    nearest_position = pos
            if nearest_position is not None:
                clusters[nearest_position].append(sample_value)
        return clusters
