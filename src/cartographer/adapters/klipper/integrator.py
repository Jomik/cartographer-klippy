from __future__ import annotations

import logging
from functools import wraps
from textwrap import dedent
from typing import TYPE_CHECKING, Callable, final

from typing_extensions import override

from cartographer.adapters.shared.endstop import KlipperEndstop, KlipperHomingState
from cartographer.adapters.shared.homing import CartographerHomingChip
from cartographer.adapters.shared.mcu.mcu import KlipperCartographerMcu
from cartographer.adapters.shared.utils import reraise_as_command_error
from cartographer.runtime.types import Integrator

if TYPE_CHECKING:
    from extras.homing import Homing
    from gcode import GCodeCommand
    from stepper import PrinterRail

    from cartographer.adapters.klipper.adapters import KlipperAdapters
    from cartographer.interfaces.printer import Endstop, Macro

logger = logging.getLogger(__name__)


@final
class KlipperIntegrator(Integrator):
    def __init__(self, adapters: KlipperAdapters) -> None:
        assert isinstance(adapters.mcu, KlipperCartographerMcu), "Invalid MCU type for KlipperIntegrator"
        self._printer = adapters.printer
        self._mcu = adapters.mcu

        self._gcode = self._printer.lookup_object("gcode")

    @override
    def setup(self) -> None:
        self._printer.register_event_handler("homing:home_rails_end", self._handle_home_rails_end)

    @override
    def register_endstop_pin(self, chip_name: str, pin: str, endstop: Endstop) -> None:
        mcu_endstop = KlipperEndstop(self._mcu, endstop)
        chip = CartographerHomingChip(self._printer, mcu_endstop, pin)
        self._printer.lookup_object("pins").register_chip(chip_name, chip)

    @override
    def register_macro(self, macro: Macro) -> None:
        self._gcode.register_command(macro.name, _catch_macro_errors(macro.run), desc=macro.description)

    @reraise_as_command_error
    def _handle_home_rails_end(self, homing: Homing, rails: list[PrinterRail]) -> None:
        homing_state = KlipperHomingState(homing)
        klipper_endstops = [
            es.endstop for rail in rails for es, _ in rail.get_endstops() if isinstance(es, KlipperEndstop)
        ]
        for endstop in klipper_endstops:
            endstop.on_home_end(homing_state)


def _catch_macro_errors(func: Callable[[GCodeCommand], None]) -> Callable[[GCodeCommand], None]:
    @wraps(func)
    def wrapper(gcmd: GCodeCommand) -> None:
        try:
            func(gcmd)
        except (RuntimeError, ValueError) as e:
            msg = dedent(str(e)).replace("\n", " ").strip()
            raise gcmd.error(msg) from e

    return wrapper
