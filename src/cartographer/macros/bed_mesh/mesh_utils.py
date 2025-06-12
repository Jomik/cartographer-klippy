from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Literal

import numpy as np

if TYPE_CHECKING:
    from cartographer.interfaces.printer import Sample
    from cartographer.macros.bed_mesh.interfaces import Point


def cluster_points(points: list[Point], axis: Literal["x", "y"], tol: float = 1e-3) -> list[list[Point]]:
    # axis to cluster on:
    # if main_direction = "x", cluster on y (index 1)
    # if main_direction = "y", cluster on x (index 0)
    cluster_index = 1 if axis == "x" else 0
    sort_index = 0 if axis == "x" else 1

    clusters: dict[float, list[Point]] = defaultdict(list)
    for p in points:
        key = round(p[cluster_index] / tol)
        clusters[key].append(p)

    sorted_keys = sorted(clusters.keys())

    rows: list[list[Point]] = []
    for key in sorted_keys:
        row_points = clusters[key]
        row_points.sort(key=lambda pt: pt[sort_index])
        rows.append(row_points)

    return rows


@dataclass(frozen=True)
class GridPointResult:
    point: Point
    z: float
    sample_count: int


def assign_samples_to_grid(
    grid: list[Point], samples: list[Sample], calculate_height: Callable[[Sample], float], max_distance: float = 1.0
) -> list[GridPointResult]:
    # Extract sorted unique coordinates
    mesh_array: np.ndarray[float, np.dtype[np.float64]] = np.array(grid)
    x_vals = np.unique(mesh_array[:, 0])
    y_vals = np.unique(mesh_array[:, 1])

    x_res = len(x_vals)
    y_res = len(y_vals)

    x_min, x_max = float(x_vals[0]), float(x_vals[-1])
    y_min, y_max = float(y_vals[0]), float(y_vals[-1])

    x_step: float = (x_max - x_min) / (x_res - 1)
    y_step: float = (y_max - y_min) / (y_res - 1)

    # Map (j, i) grid positions to (x, y)
    index_to_point: dict[tuple[int, int], Point] = {
        (j, i): (float(x), float(y)) for i, x in enumerate(x_vals) for j, y in enumerate(y_vals)
    }

    # Accumulator: (row=j, col=i) → list of z values
    accumulator: dict[tuple[int, int], list[float]] = defaultdict(list)

    for sample in samples:
        if sample.position is None:
            continue
        sx = sample.position.x
        sy = sample.position.y
        i = round((sx - x_min) / x_step)
        j = round((sy - y_min) / y_step)

        if 0 <= i < x_res and 0 <= j < y_res:
            gx: float = x_vals[i]
            gy: float = y_vals[j]
            if np.hypot(sx - gx, sy - gy) > max_distance:
                continue

            sz = calculate_height(sample)
            accumulator[(j, i)].append(sz)

    results: list[GridPointResult] = []

    for (j, i), point in index_to_point.items():
        values = accumulator.get((j, i), [])
        count = len(values)
        z = float(np.median(values))
        results.append(GridPointResult(point=point, z=z, sample_count=count))

    return results
