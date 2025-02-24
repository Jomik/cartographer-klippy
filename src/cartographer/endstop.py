from __future__ import annotations

from typing import Protocol, final

from cartographer.printer import ReactorCompletion

from .modes.base_mode import EndstopMode


class EndstopException(Exception):
    pass


class MCU(Protocol):
    def stop_homing(self, home_end_time: float) -> float: ...


@final
class Endstop:
    """Main Endstop class with switchable modes."""

    def __init__(self, mcu: MCU, mode: EndstopMode) -> None:
        self._mcu = mcu
        self._mode = mode
        self._mode.on_enter()

    def current_mode(self) -> EndstopMode:
        return self._mode

    def set_mode(self, new_mode: EndstopMode) -> None:
        """Safely switch between Scan and Touch modes."""
        if not self._mode.can_switch():
            raise EndstopException("Mode switch not allowed")

        self._mode.on_exit()
        self._mode = new_mode
        self._mode.on_enter()

    def query_triggered(self, print_time: float) -> bool:
        """Return true if endstop is currently triggered"""
        return self._mode.query_triggered(print_time)

    def get_endstop_position(self) -> float:
        """Returns the position at which the endstop is triggered"""
        return self._mode.get_endstop_position()

    def home_start(self, print_time: float) -> ReactorCompletion[bool | int]:
        """Start the homing process"""
        return self._mode.home_start(print_time)

    def home_wait(self, home_end_time: float) -> float:
        """Wait for homing to complete"""
        return self._mcu.stop_homing(home_end_time)
