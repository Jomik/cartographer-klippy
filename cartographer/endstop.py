from __future__ import annotations

from typing import final

from configfile import ConfigWrapper
from extras.probe import ProbeEndstopWrapper
from mcu import MCU, MCU_trsync, TriggerDispatch, MCU_endstop
from reactor import ReactorCompletion
from stepper import MCU_stepper
from typing_extensions import override

from cartographer.mcu import ScannerMCUHelper


@final
class ScannerEndstopWrapper(ProbeEndstopWrapper):
    def __init__(self, config: ConfigWrapper, mcu_helper: ScannerMCUHelper):
        self.printer = config.get_printer()
        self._mcu_helper = mcu_helper
        self._dispatch = TriggerDispatch(mcu_helper.get_mcu())
        self._mcu_endstop = ScanEndstop(mcu_helper)

    @override
    def get_mcu(self) -> MCU:
        return self._mcu_helper.get_mcu()

    @override
    def add_stepper(self, stepper: MCU_stepper) -> None:
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
    ) -> ReactorCompletion:
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
        raise NotImplementedError()

    @override
    def multi_probe_end(self) -> None:
        raise NotImplementedError()

    @override
    def probing_move(self, pos: "list[float]", speed: float) -> "list[float]":
        raise NotImplementedError()

    @override
    def probe_prepare(self, hmove: float) -> None:
        raise NotImplementedError()

    @override
    def probe_finish(self, hmove: float) -> None:
        raise NotImplementedError()

    @override
    def get_position_endstop(self) -> float:
        raise NotImplementedError()


@final
class ScanEndstop(MCU_endstop):
    def __init__(self, mcu_helper: ScannerMCUHelper):
        self._mcu_helper = mcu_helper
        self._dispatch = TriggerDispatch(mcu_helper.get_mcu())
        self._mcu = mcu_helper.get_mcu()

    @override
    def get_mcu(self) -> MCU:
        return self._mcu_helper.get_mcu()

    @override
    def add_stepper(self, stepper: MCU_stepper) -> None:
        self._dispatch.add_stepper(stepper)

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
    ) -> ReactorCompletion:
        # TODO: Set threshold
        trigger_completion = self._dispatch.start(print_time)
        self._mcu.get_printer().lookup_object("toolhead").wait_moves()
        self._mcu_helper.home_scan(self._dispatch.get_oid())
        return trigger_completion

    @override
    def home_wait(self, home_end_time: float) -> float:
        self._dispatch.wait_end(home_end_time)
        self._mcu_helper.stop_home()
        res = self._dispatch.stop()
        if res >= MCU_trsync.REASON_COMMS_TIMEOUT:
            raise self._mcu.get_printer().command_error(
                "Communication timeout during homing"
            )
        if res != MCU_trsync.REASON_ENDSTOP_HIT:
            return 0.0
        if self._mcu.is_fileoutput():
            return home_end_time
        # TODO: Use a query state command for actual end time
        return home_end_time

    @override
    def query_endstop(self, print_time: float) -> int:
        # TODO: Use a query state command for actual state
        sample = self._mcu_helper.get_last_sample()
        if sample is None:
            return 0
        # TODO: Read trigger frequency from model
        trigger_freq = 33784425
        if sample["freq"] > trigger_freq:
            return 1
        return 0
