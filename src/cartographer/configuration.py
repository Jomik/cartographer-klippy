from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from cartographer.probes.scan_model import Configuration as ScanModelConfiguration


class ProbeMode(Enum):
    SCAN = "scan"
    TOUCH = "touch"


class CartographerConfiguration(Protocol):
    x_offset: float
    y_offset: float
    backlash_compensation: float
    probing_mode: ProbeMode
    verbose: bool

    scan_models: dict[str, ScanModelConfiguration]
