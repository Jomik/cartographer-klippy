from __future__ import annotations

import logging
from typing import Protocol, final

from extras.probe import ProbeEndstopWrapper
from mcu import MCU, TriggerDispatch
from reactor import ReactorCompletion
from stepper import MCU_stepper
from typing_extensions import override

from cartographer.mcu.helper import McuHelper

logger = logging.getLogger(__name__)


class Endstop(Protocol):
    def get_steppers(self) -> list[MCU_stepper]: ...
    def get_position_endstop(self) -> float: ...
    def home_start(
        self,
        print_time: float,
        sample_time: float,
        sample_count: int,
        rest_time: float,
        triggered: bool = True,
    ) -> ReactorCompletion[int]: ...
    def home_wait(self, home_end_time: float) -> float: ...
    def query_endstop(self, print_time: float) -> int: ...


@final
class EndstopWrapper(ProbeEndstopWrapper):
    def __init__(
        self, mcu_helper: McuHelper, endstop: Endstop, dispatch: TriggerDispatch
    ):
        self._mcu_helper = mcu_helper
        self._printer = mcu_helper.get_mcu().get_printer()
        self._mcu_endstop = endstop
        self._dispatch = dispatch

    @override
    def get_mcu(self) -> MCU:
        return self._mcu_helper.get_mcu()

    @override
    def add_stepper(self, stepper: MCU_stepper) -> None:
        logger.debug("Adding stepper %s to endstop", stepper)
        return self._dispatch.add_stepper(stepper)

    @override
    def get_steppers(self) -> list[MCU_stepper]:
        return self._dispatch.get_steppers()

    @override
    def home_start(
        self,
        print_time: float,
        sample_time: float,
        sample_count: int,
        rest_time: float,
        triggered: bool = True,
    ) -> ReactorCompletion[int]:
        return self._mcu_endstop.home_start(
            print_time, sample_time, sample_count, rest_time, triggered
        )

    @override
    def home_wait(self, home_end_time: float) -> float:
        return self._mcu_endstop.home_wait(home_end_time)

    @override
    def query_endstop(self, print_time: float) -> int:
        return self._mcu_endstop.query_endstop(print_time)

    @override
    def multi_probe_begin(self) -> None:
        return

    @override
    def multi_probe_end(self) -> None:
        return

    @override
    def probing_move(self, pos: list[float], speed: float) -> list[float]:
        phoming = self._printer.lookup_object("homing")
        return phoming.probing_move(self, pos, speed)

    @override
    def probe_prepare(self, hmove: float) -> None:
        pass

    @override
    def probe_finish(self, hmove: float) -> None:
        pass

    @override
    def get_position_endstop(self) -> float:
        return self._mcu_endstop.get_position_endstop()
