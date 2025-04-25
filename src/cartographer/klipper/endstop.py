from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.klipper.utils import reraise_as_command_error
from cartographer.printer_interface import HomingAxis, HomingState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from extras.homing import Homing
    from mcu import MCU
    from reactor import ReactorCompletion
    from stepper import MCU_stepper, PrinterRail

    from cartographer.klipper.mcu import KlipperCartographerMcu
    from cartographer.printer_interface import Endstop

logger = logging.getLogger(__name__)

axis_mapping: dict[HomingAxis, int] = {
    "x": 0,
    "y": 1,
    "z": 2,
}


def axis_to_index(axis: HomingAxis) -> int:
    return axis_mapping[axis]


@final
class KlipperHomingState(HomingState):
    def __init__(self, homing: Homing, endstops: Sequence[Endstop[object]]) -> None:
        self.homing = homing
        self.endstops = endstops

    @override
    def is_homing_z(self) -> bool:
        return axis_to_index("z") in self.homing.get_axes()

    @override
    def set_z_homed_position(self, position: float) -> None:
        logger.debug("Setting homed distance for z to %.3f", position)
        self.homing.set_homed_position([None, None, position])


class _MemoizedEndstop(type):
    _endstops: dict[Endstop[ReactorCompletion], KlipperEndstop] = {}

    @override
    def __call__(cls, mcu: KlipperCartographerMcu, endstop: Endstop[ReactorCompletion]):
        if endstop not in cls._endstops:
            cls._endstops[endstop] = super().__call__(mcu, endstop)
        return cls._endstops[endstop]


@final
class KlipperEndstop(metaclass=_MemoizedEndstop):
    def __init__(self, mcu: KlipperCartographerMcu, endstop: Endstop[ReactorCompletion]):
        self.printer = mcu.klipper_mcu.get_printer()
        self.mcu = mcu
        self.endstop = endstop
        self.printer.register_event_handler("homing:home_rails_end", self.home_rails_end)

    @reraise_as_command_error
    def home_rails_end(self, homing: Homing, rails: list[PrinterRail]) -> None:
        endstops = [es.endstop for rail in rails for es, _ in rail.get_endstops() if isinstance(es, KlipperEndstop)]
        self.endstop.on_home_end(KlipperHomingState(homing, endstops))

    def get_mcu(self) -> MCU:
        return self.mcu.klipper_mcu

    def add_stepper(self, stepper: MCU_stepper) -> None:
        return self.mcu.dispatch.add_stepper(stepper)

    def get_steppers(self) -> list[MCU_stepper]:
        return self.mcu.dispatch.get_steppers()

    @reraise_as_command_error
    def home_start(
        self,
        print_time: float,
        sample_time: float,
        sample_count: int,
        rest_time: float,
        triggered: bool = True,
    ) -> ReactorCompletion:
        del sample_time, sample_count, rest_time, triggered
        return self.endstop.home_start(print_time)

    @reraise_as_command_error
    def home_wait(self, home_end_time: float) -> float:
        return self.endstop.home_wait(home_end_time)

    @reraise_as_command_error
    def query_endstop(self, print_time: float) -> int:
        return 1 if self.endstop.query_is_triggered(print_time) else 0

    def get_position_endstop(self) -> float:
        return self.endstop.get_endstop_position()
