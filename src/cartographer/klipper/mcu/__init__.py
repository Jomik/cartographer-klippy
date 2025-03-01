from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, TypedDict, final

import mcu
from mcu import MCU_trsync
from mcu import TriggerDispatch as KlipperTriggerDispatch
from typing_extensions import override

from cartographer.endstop import Mcu as EndstopMcu
from cartographer.klipper.mcu.commands import HomeCommand, KlipperCartographerCommands, ThresholdCommand, TriggerMethod
from cartographer.klipper.mcu.constants import (
    FREQUENCY_RANGE_PERCENT,
    SHORTED_FREQUENCY_VALUE,
    TRIGGER_HYSTERESIS,
    KlipperCartographerConstants,
)
from cartographer.klipper.stream import KlipperStream, KlipperStreamMcu
from cartographer.modes.scan_mode import Mcu as ScanModeMcu
from cartographer.modes.scan_mode import Sample

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
class KlipperCartographerMcu(EndstopMcu, ScanModeMcu, KlipperStreamMcu):
    _error: str | None = None

    def __init__(
        self,
        config: ConfigWrapper,
        smoothing_fn: Callable[[Sample], Sample] | None = None,
    ):
        printer = config.get_printer()
        self.klipper_mcu = mcu.get_printer_mcu(printer, config.get("mcu"))
        self._constants = KlipperCartographerConstants(self.klipper_mcu)
        self._commands = KlipperCartographerCommands(self.klipper_mcu)
        self._stream = KlipperStream[Sample](self, self.klipper_mcu.get_printer().get_reactor(), smoothing_fn)

        self.dispatch = KlipperTriggerDispatch(self.klipper_mcu)

        self._command_queue = self.klipper_mcu.alloc_command_queue()

        printer.register_event_handler("klippy:connect", self._handle_connect)
        printer.register_event_handler("klippy:shutdown", self._handle_shutdown)
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

    def _handle_connect(self) -> None:
        self.stop_streaming()

    def _handle_shutdown(self) -> None:
        self.stop_streaming()

    def _handle_data(self, data: _RawData) -> None:
        self._validate_data(data)
        count = data["data"]
        clock = self.klipper_mcu.clock32_to_clock64(data["clock"])
        time = self.klipper_mcu.clock_to_print_time(clock)
        # TODO: Apply smoothing
        frequency = self._constants.count_to_frequency(count)

        sample = Sample(
            time=time,
            frequency=frequency,
        )
        self._stream.add_item(sample)

    def _validate_data(self, data: _RawData) -> None:
        count = data["data"]
        if count == SHORTED_FREQUENCY_VALUE:
            self._error = "Coil is shorted or not connected."
            logger.error(self._error)
        elif count > self._constants.minimum_count * FREQUENCY_RANGE_PERCENT:
            self._error = f"coil frequency reading exceeded max expected value, received {count}"
            logger.error(self._error)

        if len(self._stream.sessions) > 0 and self._error is not None:
            self.klipper_mcu.get_printer().invoke_shutdown(self._error)
