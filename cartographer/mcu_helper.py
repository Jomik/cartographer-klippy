from __future__ import annotations

import logging
import struct
from enum import IntEnum
from typing import Optional, Tuple, TypedDict, final

from configfile import ConfigWrapper
from mcu import MCU, CommandQueryWrapper, CommandWrapper, MCU_trsync


# TODO: These probably live on the model
TRIGGER_DISTANCE = 2.0
TRIGGER_HYSTERESIS = 0.006


class RawSample(TypedDict):
    clock: int
    data: int
    temp: int


class TriggerMethod(IntEnum):
    SCAN = 0
    TOUCH = 1


class _BaseData(TypedDict):
    bytes: bytes


@final
class ScannerMCUHelper:
    _stream_command: Optional[CommandWrapper] = None
    _set_threshold_command: Optional[CommandWrapper] = None
    _start_home_command: Optional[CommandWrapper] = None
    _stop_home_command: Optional[CommandWrapper] = None
    _base_read_command: Optional[CommandQueryWrapper[_BaseData]] = None
    _sensor_frequency: float = 0.0

    _streaming = True

    def __init__(self, config: ConfigWrapper):
        printer = config.get_printer()

        mcu_name = config.get("mcu")
        self._mcu: MCU = printer.lookup_object(f"mcu {mcu_name}")
        self._command_queue = self._mcu.alloc_command_queue()

        printer.register_event_handler("klippy:connect", self._handle_connect)
        printer.register_event_handler("klippy:disconnect", self._handle_disconnect)
        printer.register_event_handler("klippy:shutdown", self._handle_shutdown)
        self._mcu.register_config_callback(self._build_config)

    def get_mcu(self) -> MCU:
        return self._mcu

    def _handle_connect(self) -> None:
        self.stop_stream()

    def _handle_disconnect(self) -> None:
        # TODO: Cleanup streaming
        pass

    def _handle_shutdown(self) -> None:
        # TODO: Cleanup streaming
        pass

    def _build_config(self) -> None:
        self._stream_command = self._mcu.lookup_command(
            "cartographer_stream en=%u", cq=self._command_queue
        )
        self._set_threshold_command = self._mcu.lookup_command(
            "cartographer_set_threshold trigger=%u untrigger=%u",
            cq=self._command_queue,
        )
        self._start_home_command = self._mcu.lookup_command(
            "cartographer_home trsync_oid=%c trigger_reason=%c trigger_invert=%c threshold=%u trigger_method=%u",
            cq=self._command_queue,
        )
        self._stop_home_command = self._mcu.lookup_command(
            "cartographer_stop_home", cq=self._command_queue
        )
        self._base_read_command = self._mcu.lookup_query_command(
            "cartographer_base_read len=%c offset=%hu",
            "cartographer_base_data bytes=%*s offset=%hu",
            cq=self._command_queue,
        )

        clock_frequency = self._mcu.get_constant_float("CLOCK_FREQ")
        logging.info(f"Cartographer clock frequency: {clock_frequency:e}")
        self._sensor_frequency = self._clock_to_sensor_frequency(clock_frequency)

    def _clock_to_sensor_frequency(self, clock_frequency: float) -> float:
        if clock_frequency < 20000000:
            return clock_frequency
        elif clock_frequency < 100000000:
            return clock_frequency / 2
        return clock_frequency / 6

    def _set_stream(self, enable: int) -> None:
        if self._stream_command is None:
            raise self._mcu.error("stream command not initialized")
        self._stream_command.send([enable])

    def start_stream(self) -> None:
        if self._streaming:
            return
        logging.info("Starting cartographer data stream")
        self._set_stream(1)
        self._streaming = True

    def stop_stream(self) -> None:
        if not self._streaming:
            return
        logging.info("Stopping cartographer data stream")
        self._set_stream(0)
        self._streaming = False

    def is_streaming(self) -> bool:
        return self._streaming

    def _frequency_to_count(self, frequency: float) -> int:
        return int(frequency * (2**28) / self._sensor_frequency)

    def count_to_frequency(self, count: int):
        return count * self._sensor_frequency / (2**28)

    def set_threshold(self, trigger_frequency: float) -> None:
        if self._set_threshold_command is None:
            raise self._mcu.error("set threshold command not initialized")

        trigger = self._frequency_to_count(trigger_frequency)
        untrigger = self._frequency_to_count(
            trigger_frequency * (1 - TRIGGER_HYSTERESIS)
        )

        self._set_threshold_command.send([trigger, untrigger])

    def _start_home(
        self,
        trsync_oid: int,
        threshold: int,
        trigger_method: TriggerMethod,
    ) -> None:
        if self._start_home_command is None:
            raise self._mcu.error("start home command not initialized")

        trigger_reason = MCU_trsync.REASON_ENDSTOP_HIT
        trigger_invert = 0

        self._start_home_command.send(
            [
                trsync_oid,
                trigger_reason,
                trigger_invert,
                threshold,
                trigger_method,
            ]
        )

    def home_scan(
        self,
        trsync_oid: int,
    ) -> None:
        self._start_home(trsync_oid, 0, TriggerMethod.SCAN)

    def stop_home(self) -> None:
        if self._stop_home_command is None:
            raise self._mcu.error("stop home command not initialized")
        self._stop_home_command.send()

    def query_base(self) -> Tuple[int, int]:
        if self._base_read_command is None:
            raise self._mcu.error("base read command is not initialized")
        fixed_length = 6
        fixed_offset = 0

        base_data = self._base_read_command.send([fixed_length, fixed_offset])

        f_count: int
        adc_count: int
        f_count, adc_count = struct.unpack("<IH", base_data["bytes"])

        if f_count >= 0xFFFFFFFF or adc_count >= 0xFFFF:
            raise self._mcu.error("invalid f_count or adc_count")

        return f_count, adc_count
