from __future__ import annotations

import logging
from functools import wraps
from textwrap import dedent
from typing import TYPE_CHECKING, Callable, final

from gcode import CommandError, GCodeCommand
from typing_extensions import override

from cartographer.adapters.klipper.endstop import KlipperEndstop, KlipperHomingState
from cartographer.adapters.klipper.homing import CartographerHomingChip
from cartographer.adapters.klipper.logging import setup_console_logger
from cartographer.adapters.klipper.mcu import KlipperCartographerMcu
from cartographer.adapters.klipper.probe import KlipperCartographerProbe
from cartographer.adapters.klipper.toolhead import KlipperToolhead
from cartographer.adapters.utils import reraise_as
from cartographer.interfaces.printer import MacroParams, SupportsFallbackMacro
from cartographer.macros.probe import ProbeMacro, QueryProbeMacro
from cartographer.runtime.integrator import Integrator

if TYPE_CHECKING:
    from extras.homing import Homing
    from stepper import PrinterRail

    from cartographer.adapters.klipper.adapters import KlipperAdapters
    from cartographer.core import PrinterCartographer
    from cartographer.interfaces.printer import Endstop, Macro

logger = logging.getLogger(__name__)


@final
class KlipperIntegrator(Integrator):
    def __init__(self, adapters: KlipperAdapters) -> None:
        assert isinstance(adapters.mcu, KlipperCartographerMcu), "invalid MCU type for KlipperIntegrator"
        assert isinstance(adapters.toolhead, KlipperToolhead), "invalid toolhead type for KlipperIntegrator"
        self._adapters = adapters
        self._printer = adapters.printer
        self._mcu = adapters.mcu
        self._toolhead = adapters.toolhead

        self._gcode = self._printer.lookup_object("gcode")

    @override
    def setup(self) -> None:
        self._printer.register_event_handler("homing:home_rails_end", self._handle_home_rails_end)
        self._configure_macro_logger()

    @override
    def register_cartographer(self, cartographer: PrinterCartographer) -> None:
        try:
            probe_macro = next(macro for macro in cartographer.macros if isinstance(macro, ProbeMacro))
            query_probe_macro = next(macro for macro in cartographer.macros if isinstance(macro, QueryProbeMacro))
        except StopIteration:
            msg = "Required macros (PROBE, QUERY_PROBE) not found in cartographer."
            raise ValueError(msg) from None

        self._printer.add_object(
            "probe",
            KlipperCartographerProbe(
                self._toolhead,
                cartographer.scan_mode,
                probe_macro,
                query_probe_macro,
            ),
        )

    @override
    def register_endstop_pin(self, chip_name: str, pin: str, endstop: Endstop) -> None:
        mcu_endstop = KlipperEndstop(self._mcu, endstop)
        chip = CartographerHomingChip(mcu_endstop, pin)
        self._printer.lookup_object("pins").register_chip(chip_name, chip)

    @override
    def register_macro(self, macro: Macro) -> None:
        original = self._gcode.register_command(macro.name, None)
        if isinstance(macro, SupportsFallbackMacro):
            if original:
                macro.set_fallback_macro(FallbackMacroAdapter(macro.name, original))
            else:
                logger.warning("No original macro found to fallback to for '%s'", macro.name)

        self._gcode.register_command(macro.name, _catch_macro_errors(macro.run), desc=macro.description)

    @reraise_as(CommandError)
    def _handle_home_rails_end(self, homing: Homing, rails: list[PrinterRail]) -> None:
        homing_state = KlipperHomingState(homing)
        klipper_endstops = [
            es.endstop for rail in rails for es, _ in rail.get_endstops() if isinstance(es, KlipperEndstop)
        ]
        for endstop in klipper_endstops:
            endstop.on_home_end(homing_state)

    def _configure_macro_logger(self) -> None:
        handler = setup_console_logger(self._gcode)

        log_level = logging.DEBUG if self._adapters.config.general.verbose else logging.INFO
        handler.setLevel(log_level)


def _catch_macro_errors(func: Callable[[GCodeCommand], None]) -> Callable[[GCodeCommand], None]:
    @wraps(func)
    def wrapper(gcmd: GCodeCommand) -> None:
        try:
            func(gcmd)
        except (RuntimeError, ValueError) as e:
            msg = dedent(str(e)).replace("\n", " ").replace("  ", "\n").strip()
            raise gcmd.error(msg) from e

    return wrapper


class FallbackMacroAdapter:
    def __init__(self, name: str, handler: Callable[[GCodeCommand], None]) -> None:
        self.name: str = name
        self.description: str = f"Fallback for {name}"
        self._handler: Callable[[GCodeCommand], None] = handler

    def run(self, params: MacroParams) -> None:
        assert isinstance(params, GCodeCommand), f"Invalid gcode params type for {self.name}"
        self._handler(params)
