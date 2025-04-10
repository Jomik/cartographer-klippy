from __future__ import annotations

from enum import Enum
from typing import Protocol


class ProbeMode(Enum):
    SCAN = "scan"
    TOUCH = "touch"


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
    touch_retries: int

    # [cartographer scan_model default]
    scan_models: dict[str, ScanModelConfiguration]

    # [cartographer touch_model default]
    touch_models: dict[str, TouchModelConfiguration]


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
