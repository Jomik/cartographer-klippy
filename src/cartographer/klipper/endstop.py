from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from mcu import MCU_endstop
from typing_extensions import override

from cartographer.klipper.printer import KlipperHomingState

if TYPE_CHECKING:
    from extras.homing import Homing
    from mcu import MCU
    from reactor import ReactorCompletion
    from stepper import MCU_stepper, PrinterRail

    from cartographer.klipper.mcu import KlipperCartographerMcu
    from cartographer.printer_interface import Endstop

logger = logging.getLogger(__name__)


@final
class KlipperEndstop(MCU_endstop):
    def __init__(self, mcu: KlipperCartographerMcu, endstop: Endstop[ReactorCompletion]):
        self.printer = mcu.klipper_mcu.get_printer()
        self.mcu = mcu
        self.endstop = endstop
        self.printer.register_event_handler("homing:home_rails_end", self.home_rails_end)

    def home_rails_end(self, homing: Homing, rails: list[PrinterRail]) -> None:
        endstops = [es.endstop for rail in rails for es, _ in rail.get_endstops() if isinstance(es, KlipperEndstop)]
        self.endstop.on_home_end(KlipperHomingState(homing, endstops))

    @override
    def get_mcu(self) -> MCU:
        return self.mcu.klipper_mcu

    @override
    def add_stepper(self, stepper: MCU_stepper) -> None:
        logger.debug("Adding stepper %s to endstop", stepper.get_name())
        return self.mcu.dispatch.add_stepper(stepper)

    @override
    def get_steppers(self) -> list[MCU_stepper]:
        return self.mcu.dispatch.get_steppers()

    @override
    def home_start(
        self,
        print_time: float,
        sample_time: float,
        sample_count: int,
        rest_time: float,
        triggered: bool = True,
    ) -> ReactorCompletion:
        return self.endstop.home_start(print_time)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self.endstop.home_wait(home_end_time)

    @override
    def query_endstop(self, print_time: float) -> int:
        return 1 if self.endstop.query_is_triggered(print_time) else 0

    @override
    def get_position_endstop(self) -> float:
        return self.endstop.get_endstop_position()
