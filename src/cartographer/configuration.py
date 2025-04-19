from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ProbeMethod(Enum):
    SCAN = "scan"
    TOUCH = "touch"


@dataclass
class ScanModelFit:
    coefficients: list[float]
    domain: tuple[float, float]


class Configuration(Protocol):
    # [cartographer]
    x_offset: float
    y_offset: float
    backlash_compensation: float
    move_speed: float
    verbose: bool

    # [cartographer scan]
    scan_samples: int
    scan_mesh_runs: int

    # [cartographer touch]
    touch_samples: int
    touch_max_samples: int

    # [cartographer scan_model default]
    scan_models: dict[str, ScanModelConfiguration]

    # [cartographer touch_model default]
    touch_models: dict[str, TouchModelConfiguration]

    # [bed_mesh]
    mesh_min: tuple[float, float]
    mesh_max: tuple[float, float]
    scan_speed: float
    scan_height: float
    zero_reference_position: tuple[float, float]

    def save_new_scan_model(self, name: str, model: ScanModelFit) -> ScanModelConfiguration: ...
    def save_new_touch_model(self, name: str, speed: float, threshold: int) -> TouchModelConfiguration: ...


class ScanModelConfiguration(Protocol):
    name: str
    coefficients: list[float]
    domain: tuple[float, float]
    z_offset: float

    def save_z_offset(self, new_offset: float) -> None: ...


class TouchModelConfiguration(Protocol):
    name: str
    threshold: int
    speed: float
    z_offset: float

    def save_z_offset(self, new_offset: float) -> None: ...
