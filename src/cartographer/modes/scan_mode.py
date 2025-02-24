from __future__ import annotations

import logging
from typing import Protocol, final

from typing_extensions import override

from cartographer.printer import HomingState, ReactorCompletion

from .base_mode import EndstopMode

logger = logging.getLogger(__name__)

TRIGGER_DISTANCE = 2.0


class Model(Protocol):
    def distance_to_frequency(self, distance: float) -> float: ...


class Toolhead(Protocol):
    def get_last_move_time(self) -> float: ...
    def wait_moves(self) -> None: ...


class MCU(Protocol):
    def start_homing_scan(self, frequency: float) -> ReactorCompletion[bool | int]: ...


@final
class ScanMode(EndstopMode):
    """Implementation for Scan mode."""

    def __init__(self, toolhead: Toolhead, mcu: MCU, model: Model) -> None:
        self._toolhead = toolhead
        self._mcu = mcu
        self._model = model

        self._trigger_distance = TRIGGER_DISTANCE

    @override
    def on_enter(self) -> None:
        logger.info("Entering Scan Mode")

    @override
    def on_exit(self) -> None:
        logger.info("Exiting Scan Mode")

    @override
    def query_triggered(self, print_time: float) -> bool:
        raise NotImplementedError

    @override
    def get_endstop_position(self) -> float:
        return self._trigger_distance

    @override
    def home_start(self, print_time: float) -> ReactorCompletion[bool | int]:
        self._toolhead.wait_moves()
        return self._mcu.start_homing_scan(
            self._model.distance_to_frequency(self.get_endstop_position())
        )

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        raise NotImplementedError
