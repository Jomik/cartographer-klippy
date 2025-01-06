from __future__ import annotations

import logging
import math
from typing import Protocol, final

import numpy as np
from extras.homing import Homing, HomingMove
from mcu import MCU, MCU_trsync, TriggerDispatch
from reactor import ReactorCompletion
from stepper import MCU_stepper, PrinterRail
from typing_extensions import override

from cartographer.endstop_wrapper import Endstop
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import StreamHandler
from cartographer.scan.calibration.model import TRIGGER_DISTANCE
from cartographer.scan.stream import Sample, scan_session

logger = logging.getLogger(__name__)


class Model(Protocol):
    def frequency_to_distance(self, frequency: float) -> float: ...
    def distance_to_frequency(self, distance: float) -> float: ...


@final
class ScanEndstop(Endstop):
    def __init__(
        self,
        mcu_helper: McuHelper,
        model: Model,
        stream_handler: StreamHandler,
    ):
        self._mcu_helper = mcu_helper
        self._stream_handler = stream_handler
        self._printer = mcu_helper.get_printer()
        self._dispatch = TriggerDispatch(mcu_helper.get_mcu())
        self._model = model
        self._printer.register_event_handler(
            "homing:home_rails_end", self._handle_home_rails_end
        )
        self._printer.register_event_handler(
            "homing:homing_move_end", self._handle_homing_move_end
        )
        self._is_homing = False

    def _handle_home_rails_end(
        self, homing_state: Homing, _rails: list[PrinterRail]
    ) -> None:
        if not self._is_homing:
            return

        if 2 not in homing_state.get_axes():
            return
        samples = self._get_samples_synced(skip=5, count=10)
        dist = float(np.median([sample.distance for sample in samples]))
        if math.isinf(dist):
            raise self._printer.command_error("Toolhead stopped below model range")
        logger.debug(f"Setting homed distance to {dist}")
        homing_state.set_homed_position([None, None, dist])

    def _handle_homing_move_end(self, _: HomingMove) -> None:
        self._is_homing = False

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
    ) -> ReactorCompletion[bool]:
        self._mcu_helper.set_threshold(
            self._model.distance_to_frequency(TRIGGER_DISTANCE)
        )
        trigger_completion = self._dispatch.start(print_time)
        self._printer.lookup_object("toolhead").wait_moves()
        self._mcu_helper.home_scan(self._dispatch.get_oid())
        self._is_homing = True
        return trigger_completion

    @override
    def home_wait(self, home_end_time: float) -> float:
        self._dispatch.wait_end(home_end_time)
        self._mcu_helper.stop_home()
        res = self._dispatch.stop()
        if res >= MCU_trsync.REASON_COMMS_TIMEOUT:
            raise self._printer.command_error("Communication timeout during homing")
        if res != MCU_trsync.REASON_ENDSTOP_HIT:
            return 0.0
        if self.get_mcu().is_fileoutput():
            return home_end_time
        # TODO: Use a query state command for actual end time
        return home_end_time

    def _get_samples(
        self, start_time: float, skip: int = 0, count: int = 10
    ) -> list[Sample]:
        samples: list[Sample] = []
        total = skip + count

        def callback(sample: Sample) -> bool:
            if sample.time < start_time:
                return False
            samples.append(sample)
            return len(samples) >= total

        with scan_session(
            self._stream_handler, self._mcu_helper, self._model, callback
        ) as session:
            session.wait()

        return samples[skip:]

    def _get_samples_synced(self, skip: int = 0, count: int = 10) -> list[Sample]:
        move_time = self._printer.lookup_object("toolhead").get_last_move_time()
        return self._get_samples(move_time, skip, count)

    def _get_sample(self, print_time: float) -> Sample:
        return self._get_samples(print_time, count=1)[0]

    @override
    def query_endstop(self, print_time: float) -> int:
        # TODO: Use a query state command for actual state
        sample = self._get_sample(print_time)

        if sample.distance < TRIGGER_DISTANCE:
            return 1
        return 0

    @override
    def get_position_endstop(self) -> float:
        return TRIGGER_DISTANCE
