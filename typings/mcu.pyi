# https://github.com/Klipper3d/klipper/blob/master/klippy/mcu.py

from typing import Any, Callable, Protocol, TypedDict, TypeVar, overload

from cffi import FFI
from klippy import Printer
from reactor import ReactorCompletion
from stepper import MCU_stepper

T = TypeVar("T")

class error(Exception): ...

class _MCUStatus(TypedDict):
    mcu_version: str

class _CommandQueue: ...

class MCU:
    error: type[error]

    class sentinel: ...

    def alloc_command_queue(self) -> _CommandQueue: ...
    def register_config_callback(self, callback: Callable[[], None]) -> None: ...
    def register_response(
        self, callback: Callable[[T], None], message: str, oid: int | None = None
    ) -> None: ...
    def get_constants(self) -> dict[str, object]: ...
    def lookup_command(
        self, msgformat: str, cq: _CommandQueue | None = None
    ) -> CommandWrapper: ...
    def lookup_query_command(
        self,
        msgformat: str,
        respformat: str,
        oid: int | None = None,
        cq: _CommandQueue | None = None,
        is_async: bool = False,
    ) -> CommandQueryWrapper: ...
    def print_time_to_clock(self, print_time: float) -> int: ...
    def clock_to_print_time(self, clock: int) -> float: ...
    def clock32_to_clock64(self, clock32: int) -> int: ...
    def get_printer(self) -> Printer: ...
    def get_status(self) -> _MCUStatus: ...
    def is_fileoutput(self) -> bool: ...
    @overload
    def get_constant(
        self, name: str, default: type[sentinel] | str = sentinel
    ) -> str: ...
    @overload
    def get_constant(self, name: str, default: None) -> str | None: ...
    @overload
    def get_constant_float(
        self, name: str, default: type[sentinel] | float = sentinel
    ) -> float: ...
    @overload
    def get_constant_float(self, name: str, default: None) -> float | None: ...

class MCU_trsync:
    REASON_ENDSTOP_HIT: int
    REASON_HOST_REQUEST: int
    REASON_PAST_END_TIME: int
    REASON_COMMS_TIMEOUT: int

    def __init__(self, mcu: MCU, trdispatch: FFI.CData) -> None: ...
    def get_oid(self) -> int: ...
    def get_mcu(self) -> MCU: ...
    def add_stepper(self, stepper: MCU_stepper) -> None: ...
    def get_steppers(self) -> list[MCU_stepper]: ...
    def start(
        self,
        print_time: float,
        report_offset: float,
        trigger_completion: ReactorCompletion,
        expire_timeout: float,
    ) -> None: ...
    def set_home_end_time(self, home_end_time: float) -> None: ...
    def stop(self) -> int: ...

class CommandWrapper:
    def send(
        self, data: list[int] = [], minclock: int = 0, reqclock: int = 0
    ) -> None: ...

class CommandQueryWrapper[T = Any]:
    def send(self, data: list[int] = [], minclock: int = 0, reqclock: int = 0) -> T: ...

class TriggerDispatch:
    def __init__(self, mcu: MCU) -> None: ...
    def get_oid(self) -> int: ...
    def get_command_queue(self) -> _CommandQueue: ...
    def add_stepper(self, stepper: MCU_stepper) -> None: ...
    def get_steppers(self) -> list[MCU_stepper]: ...
    def start(self, print_time: float) -> ReactorCompletion: ...
    def wait_end(self, end_time: float) -> None: ...
    def stop(self) -> int: ...

class MCU_endstop(Protocol):
    def get_mcu(self) -> MCU: ...
    def add_stepper(self, stepper: MCU_stepper) -> None: ...
    def get_steppers(self) -> list[MCU_stepper]: ...
    def home_start(
        self,
        print_time: float,
        sample_time: float,
        sample_count: int,
        rest_time: float,
        triggered: bool = True,
    ) -> ReactorCompletion: ...
    def home_wait(self, home_end_time: float) -> float: ...
    def query_endstop(self, print_time: float) -> int: ...
