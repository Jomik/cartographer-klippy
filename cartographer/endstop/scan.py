from __future__ import annotations

import math
from typing import final

import numpy as np
from extras.homing import Homing
from mcu import MCU, MCU_endstop, MCU_trsync, TriggerDispatch
from reactor import ReactorCompletion
from stepper import MCU_stepper, PrinterRail
from typing_extensions import override

from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import StreamHandler

from .model import TRIGGER_DISTANCE, ScanModel
from .rich_stream import RichSample, rich_session


@final
class ScanEndstop(MCU_endstop):
    def __init__(
        self,
        mcu_helper: McuHelper,
        model: ScanModel,
    ):
        self._mcu_helper = mcu_helper
        self._stream_handler = StreamHandler(
            mcu_helper.get_mcu().get_printer(), mcu_helper
        )
        self._mcu = mcu_helper.get_mcu()
        self._printer = self._mcu.get_printer()
        self._dispatch = TriggerDispatch(self._mcu)
        self._model = model
        self._printer.register_event_handler(
            "homing:home_rails_end", self._handle_home_rails_end
        )

    def _handle_home_rails_end(
        self, homing_state: Homing, _rails: list[PrinterRail]
    ) -> None:
        if 2 not in homing_state.get_axes():
            return
        samples = self._get_samples_synced(skip=5, count=10)
        dist = float(np.median([sample.distance for sample in samples]))
        if math.isinf(dist):
            raise self._printer.command_error("Toolhead stopped below model range")
        homing_state.set_homed_position([None, None, dist])

    @override
    def get_mcu(self) -> MCU:
        return self._mcu

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
    ) -> ReactorCompletion[bool]:
        self._mcu_helper.set_threshold(
            self._model.distance_to_frequency(TRIGGER_DISTANCE)
        )
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

    def _get_samples(
        self, start_time: float, skip: int = 0, count: int = 10
    ) -> list[RichSample]:
        samples: list[RichSample] = []
        total = skip + count

        def callback(sample: RichSample) -> bool:
            if sample.time < start_time:
                return False
            samples.append(sample)
            return len(samples) >= total

        with rich_session(
            self._stream_handler, self._mcu_helper, self._model, callback
        ) as session:
            session.wait()

        return samples[skip:]

    def _get_samples_synced(self, skip: int = 0, count: int = 10) -> list[RichSample]:
        move_time = self._printer.lookup_object("toolhead").get_last_move_time()
        return self._get_samples(move_time, skip, count)

    def _get_sample(self, print_time: float) -> RichSample:
        return self._get_samples(print_time, count=1)[0]

    @override
    def query_endstop(self, print_time: float) -> int:
        # TODO: Use a query state command for actual state
        sample = self._get_sample(print_time)

        if sample.distance < TRIGGER_DISTANCE:
            return 1
        return 0
