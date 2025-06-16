from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class GeneralConfig:
    x_offset: float
    y_offset: float
    z_backlash: float
    travel_speed: float
    verbose: bool


@dataclass(frozen=True)
class ScanConfig:
    samples: int
    models: dict[str, ScanModelConfiguration]
    mesh_runs: int
    mesh_direction: Literal["x", "y"]
    mesh_height: float


@dataclass(frozen=True)
class TouchConfig:
    samples: int
    max_samples: int
    models: dict[str, TouchModelConfiguration]


@dataclass(frozen=True)
class BedMeshConfig:
    mesh_min: tuple[float, float]
    mesh_max: tuple[float, float]
    mesh_points: tuple[int, int]
    speed: float
    horizontal_move_z: float
    zero_reference_position: tuple[float, float]


@dataclass(frozen=True)
class ScanModelConfiguration:
    name: str
    coefficients: list[float]
    domain: tuple[float, float]
    z_offset: float


@dataclass(frozen=True)
class TouchModelConfiguration:
    name: str
    threshold: int
    speed: float
    z_offset: float


class Configuration(Protocol):
    general: GeneralConfig
    scan: ScanConfig
    touch: TouchConfig
    bed_mesh: BedMeshConfig

    def save_scan_model(self, config: ScanModelConfiguration) -> None: ...
    def save_touch_model(self, config: TouchModelConfiguration) -> None: ...
    def save_z_backlash(self, backlash: float) -> None: ...
