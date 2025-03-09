from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, TypedDict, final

import mcu
from mcu import MCU_trsync
from mcu import TriggerDispatch as KlipperTriggerDispatch
from typing_extensions import override

from cartographer.endstops.scan_endstop import Mcu as ScanEndstopMcu
from cartographer.endstops.scan_endstop import Sample
from cartographer.endstops.touch_endstop import Mcu as TouchEndstopMcu
from cartographer.klipper.mcu.commands import HomeCommand, KlipperCartographerCommands, ThresholdCommand, TriggerMethod
from cartographer.klipper.mcu.constants import (
    FREQUENCY_RANGE_PERCENT,
    SHORTED_FREQUENCY_VALUE,
    TRIGGER_HYSTERESIS,
    KlipperCartographerConstants,
)
from cartographer.klipper.mcu.stream import KlipperStream, KlipperStreamMcu

if TYPE_CHECKING:
    from configfile import ConfigWrapper

    from cartographer.stream import Session

logger = logging.getLogger(__name__)


class McuError(Exception):
    pass


class _RawData(TypedDict):
    clock: int
    data: int
    temp: int


@final
class KlipperCartographerMcu(ScanEndstopMcu, TouchEndstopMcu, KlipperStreamMcu):
    def __init__(
        self,
        config: ConfigWrapper,
        smoothing_fn: Callable[[Sample], Sample] | None = None,
    ):
        self.printer = config.get_printer()
        self.klipper_mcu = mcu.get_printer_mcu(self.printer, config.get("mcu"))
        self._constants = KlipperCartographerConstants(self.klipper_mcu)
        self._commands = KlipperCartographerCommands(self.klipper_mcu)
        self._stream = KlipperStream[Sample](self, self.klipper_mcu.get_printer().get_reactor(), smoothing_fn)

        self.dispatch = KlipperTriggerDispatch(self.klipper_mcu)

        self._command_queue = self.klipper_mcu.alloc_command_queue()

        self.printer.register_event_handler("klippy:mcu_identify", self._handle_mcu_identify)
        self.printer.register_event_handler("klippy:connect", self._handle_connect)
        self.printer.register_event_handler("klippy:shutdown", self._handle_shutdown)
        self.klipper_mcu.register_response(self._handle_data, "cartographer_data")

    @override
    def start_homing_scan(self, print_time: float, frequency: float) -> object:
        self._set_threshold(frequency)
        completion = self.dispatch.start(print_time)

        self._commands.send_home(
            HomeCommand(
                trsync_oid=self.dispatch.get_oid(),
                trigger_reason=MCU_trsync.REASON_ENDSTOP_HIT,
                trigger_invert=0,
                threshold=0,
                trigger_method=TriggerMethod.SCAN,
            )
        )
        return completion

    @override
    def start_homing_touch(self, print_time: float, threshold: int) -> object:
        completion = self.dispatch.start(print_time)

        self._commands.send_home(
            HomeCommand(
                trsync_oid=self.dispatch.get_oid(),
                trigger_reason=MCU_trsync.REASON_ENDSTOP_HIT,
                trigger_invert=0,
                threshold=threshold,
                trigger_method=TriggerMethod.TOUCH,
            )
        )
        return completion

    @override
    def stop_homing(self, home_end_time: float) -> float:
        self.dispatch.wait_end(home_end_time)
        self._commands.send_stop_home()
        result = self.dispatch.stop()
        if result >= MCU_trsync.REASON_COMMS_TIMEOUT:
            msg = "communication timeout during homing"
            raise self.klipper_mcu.error(msg)
        if result != MCU_trsync.REASON_ENDSTOP_HIT:
            return 0.0
        if self.klipper_mcu.is_fileoutput():
            return home_end_time
        # TODO: Use a query state command for actual end time
        return home_end_time

    @override
    def start_session(self, start_condition: Callable[[Sample], bool] | None = None) -> Session[Sample]:
        return self._stream.start_session(start_condition)

    def register_callback(self, callback: Callable[[Sample], None]) -> None:
        return self._stream.register_callback(callback)

    @override
    def start_streaming(self) -> None:
        logger.debug("Starting stream")
        self._commands.send_stream_state(enable=True)

    @override
    def stop_streaming(self) -> None:
        logger.debug("Stopping stream")
        self._commands.send_stream_state(enable=False)

    def _set_threshold(self, trigger_frequency: float) -> None:
        logger.debug("Setting threshold to %d", trigger_frequency)
        trigger = self._constants.frequency_to_count(trigger_frequency)
        untrigger = self._constants.frequency_to_count(trigger_frequency * (1 - TRIGGER_HYSTERESIS))

        self._commands.send_threshold(ThresholdCommand(trigger, untrigger))

    def _handle_mcu_identify(self) -> None:
        kin = self.printer.lookup_object("toolhead").get_kinematics()
        for stepper in kin.get_steppers():
            if stepper.is_active_axis("z"):
                self.dispatch.add_stepper(stepper)

    def _handle_connect(self) -> None:
        self.stop_streaming()

    def _handle_shutdown(self) -> None:
        self.stop_streaming()

    def _handle_data(self, data: _RawData) -> None:
        self._validate_data(data)
        clock = self.klipper_mcu.clock32_to_clock64(data["clock"])
        time = self.klipper_mcu.clock_to_print_time(clock)

        # TODO: Apply smoothing
        frequency = self._constants.count_to_frequency(data["data"])

        temperature = self._constants.calculate_temperature(data["temp"])

        sample = Sample(time=time, frequency=frequency, temperature=temperature)
        self._stream.add_item(sample)

    _data_error: str | None = None

    def _validate_data(self, data: _RawData) -> None:
        count = data["data"]
        error: str | None = None
        if count == SHORTED_FREQUENCY_VALUE:
            error = "Coil is shorted or not connected."
        elif count > self._constants.minimum_count * FREQUENCY_RANGE_PERCENT:
            error = "Coil frequency reading exceeded max expected value, received %(data)d"

        if self._data_error == error:
            return
        self._data_error = error

        if error is None:
            return

        logger.error(error, data)
        if len(self._stream.sessions) > 0:
            self.klipper_mcu.get_printer().invoke_shutdown(error % data)
