from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, final

from typing_extensions import override

from cartographer.printer import Endstop

if TYPE_CHECKING:
    from cartographer.modes.base_mode import EndstopMode
    from cartographer.printer import HomingState


class Mcu(Protocol):
    def stop_homing(self, home_end_time: float) -> float: ...


@final
class DynamicEndstop(Endstop):
    """Main Endstop class with switchable modes."""

    def __init__(self, mcu: Mcu, mode: EndstopMode) -> None:
        self._mcu = mcu
        self._mode = mode
        self._mode.on_enter()

    def current_mode(self) -> EndstopMode:
        return self._mode

    def set_mode(self, new_mode: EndstopMode) -> None:
        """Safely switch between Scan and Touch modes."""
        if not self._mode.can_switch():
            msg = "mode switch not allowed"
            raise RuntimeError(msg)

        self._mode.on_exit()
        self._mode = new_mode
        self._mode.on_enter()

    @override
    def query_is_triggered(self, print_time: float) -> bool:
        return self._mode.query_is_triggered(print_time)

    @override
    def get_endstop_position(self) -> float:
        return self._mode.get_endstop_position()

    @override
    def home_start(self, print_time: float) -> object:
        return self._mode.home_start(print_time)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu.stop_homing(home_end_time)

    @override
    def on_home_end(self, homing_state: HomingState) -> None:
        self._mode.on_home_end(homing_state)
