from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, Literal, Protocol, TypeVar

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cartographer.stream import Session

HomingAxis = Literal["x", "y", "z"]


@dataclass
class Position:
    x: float
    y: float
    z: float


class HomingState(Protocol):
    endstops: Sequence[Endstop[object]]

    def is_homing_z(self) -> bool:
        """Check if the z axis is currently being homed."""
        ...

    def set_z_homed_position(self, position: float) -> None:
        """Set the homed position for the z axis."""
        ...


class Toolhead(Protocol):
    def get_last_move_time(self) -> float:
        """Returns the last time the toolhead moved."""
        ...

    def wait_moves(self) -> None:
        """Wait for all moves to complete."""
        ...

    def get_position(self) -> Position:
        """Get the currently commanded position of the toolhead."""
        ...

    def get_requested_position(self, time: float) -> Position:
        """Get the requested position of the toolhead at the given time."""
        ...

    def manual_move(self, *, x: float = ..., y: float = ..., z: float = ..., speed: float) -> None:
        """Move to requested position."""
        ...

    def is_homed(self, axis: HomingAxis) -> bool:
        """Check if axis is homed."""
        ...

    def get_gcode_z_offset(self) -> float:
        """Returns currently applied gcode offset for the z axis."""
        ...

    def z_homing_move(self, endstop: Endstop[C], *, bottom: float, speed: float) -> float:
        """Starts homing move towards the given endstop."""
        ...


C = TypeVar("C", covariant=True)


class Endstop(Generic[C], Protocol):
    def query_is_triggered(self, print_time: float) -> bool:
        """Return true if endstop is currently triggered"""
        ...

    def home_start(self, print_time: float) -> C:
        """Start the homing process"""
        ...

    def home_wait(self, home_end_time: float) -> float:
        """Wait for homing to complete"""
        ...

    def on_home_end(self, homing_state: HomingState) -> None:
        """To be called when the homing process is complete"""
        ...

    def get_endstop_position(self) -> float:
        """The position of the endstop on the rail"""
        ...


class Sample(Protocol):
    frequency: float
    time: float


S = TypeVar("S", bound=Sample)


class Mcu(Generic[C, S], Protocol):
    def start_homing_scan(self, print_time: float, frequency: float) -> C: ...
    def start_homing_touch(self, print_time: float, threshold: int) -> C: ...
    def stop_homing(self, home_end_time: float) -> float: ...
    def start_session(self, start_condition: Callable[[S], bool] | None = None) -> Session[S]: ...


class MacroParams(Protocol):
    def get(self, name: str, default: str = ...) -> str: ...
    def get_float(self, name: str, default: float = ..., *, above: float = ..., minval: float = ...) -> float: ...
    def get_int(self, name: str, default: int = ..., *, minval: int = ...) -> int: ...


class Macro(Protocol):
    name: str
    description: str

    def run(self, params: MacroParams) -> None: ...


class Probe(Protocol):
    probe_height: float

    def probe(self, *, speed: float) -> float: ...
    def query_is_triggered(self, print_time: float) -> bool: ...
