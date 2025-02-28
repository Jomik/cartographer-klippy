from __future__ import annotations
import logging
from typing import cast, final
from extras.homing import Homing
from mcu import MCU
from reactor import ReactorCompletion
from stepper import MCU_stepper, PrinterRail
from typing_extensions import override

from extras.probe import ProbeEndstopWrapper

from cartographer.endstop import Endstop
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.printer import HomingAxis, HomingState

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
    def __init__(self, homing: Homing):
        self.homing = homing

    @override
    def is_homing(self, axis: HomingAxis) -> bool:
        return axis_to_index(axis) in self.homing.get_axes()

    @override
    def set_homed_position(self, axis: HomingAxis, position: float) -> None:
        coords: list[float | None] = [None, None, None]
        coords[axis_to_index(axis)] = position
        self.homing.set_homed_position(coords)


@final
class EndstopWrapper(ProbeEndstopWrapper):
    def __init__(self, mcu: KlipperCartographerMcu, endstop: Endstop):
        self.printer = mcu.klipper_mcu.get_printer()
        self.mcu = mcu
        self.endstop = endstop
        self.printer.register_event_handler(
            "homing:home_rails_end", self.home_rails_end
        )

    def home_rails_end(self, homing: Homing, _: list[PrinterRail]) -> None:
        self.endstop.on_home_end(KlipperHomingState(homing))

    @override
    def get_mcu(self) -> MCU:
        return self.mcu.klipper_mcu

    @override
    def add_stepper(self, stepper: MCU_stepper) -> None:
        logger.debug("Adding stepper %s to endstop", stepper)
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
    ) -> ReactorCompletion[int]:
        completion = self.endstop.home_start(print_time)
        # TODO: Consider making Endstop generic so that the home_start return type can be specified
        return cast(ReactorCompletion[int], completion)

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self.endstop.home_wait(home_end_time)

    @override
    def query_endstop(self, print_time: float) -> int:
        return self.endstop.query_triggered(print_time)

    @override
    def multi_probe_begin(self) -> None:
        pass

    @override
    def multi_probe_end(self) -> None:
        pass

    @override
    def probing_move(self, pos: list[float], speed: float) -> list[float]:
        phoming = self.mcu.klipper_mcu.get_printer().lookup_object("homing")
        return phoming.probing_move(self, pos, speed)

    @override
    def probe_prepare(self, hmove: float) -> None:
        pass

    @override
    def probe_finish(self, hmove: float) -> None:
        pass

    @override
    def get_position_endstop(self) -> float:
        return self.endstop.get_endstop_position()
