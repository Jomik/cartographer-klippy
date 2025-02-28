from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple, final

from mcu import MCU as KlipperMCU, CommandWrapper


class TriggerMethod(IntEnum):
    SCAN = 0
    TOUCH = 1


class HomeCommand(NamedTuple):
    trsync_oid: int
    trigger_reason: int
    trigger_invert: int
    threshold: int
    trigger_method: TriggerMethod


class ThresholdCommand(NamedTuple):
    trigger: int
    untrigger: int


@final
class KlipperCartographerCommands:
    def __init__(self, mcu: KlipperMCU):
        self._mcu = mcu
        self._command_queue = self._mcu.alloc_command_queue()
        self._stream_command: CommandWrapper | None = None
        self._set_threshold_command: CommandWrapper | None = None
        self._start_home_command: CommandWrapper | None = None
        self._stop_home_command: CommandWrapper | None = None
        self._mcu.register_config_callback(self._register_commands)

    def _register_commands(self) -> None:
        self._stream_command = self._mcu.lookup_command(
            "cartographer_stream en=%u", cq=self._command_queue
        )
        self._set_threshold_command = self._mcu.lookup_command(
            "cartographer_set_threshold trigger=%u untrigger=%u", cq=self._command_queue
        )
        self._start_home_command = self._mcu.lookup_command(
            "cartographer_home trsync_oid=%c trigger_reason=%c trigger_invert=%c threshold=%u trigger_method=%u",
            cq=self._command_queue,
        )
        self._stop_home_command = self._mcu.lookup_command(
            "cartographer_stop_home", cq=self._command_queue
        )

    def _ensure_initialized(
        self, command: CommandWrapper | None, name: str
    ) -> CommandWrapper:
        if command is None:
            raise RuntimeError(f"Command {name} has not been initialized.")
        return command

    def send_stream(self, enable: bool) -> None:
        command = self._ensure_initialized(self._stream_command, "stream command")
        command.send([1 if enable else 0])

    def send_threshold(self, command: ThresholdCommand) -> None:
        cmd = self._ensure_initialized(
            self._set_threshold_command, "set threshold command"
        )
        cmd.send(list(command))

    def send_home(self, command: HomeCommand) -> None:
        cmd = self._ensure_initialized(self._start_home_command, "start home command")
        cmd.send(list(command))

    def send_stop_home(self) -> None:
        cmd = self._ensure_initialized(self._stop_home_command, "stop home command")
        cmd.send()
