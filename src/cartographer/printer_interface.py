from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, Literal, NamedTuple, Protocol, TypeVar, overload

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cartographer.stream import Session

HomingAxis = Literal["x", "y", "z"]


@dataclass
class Position:
    x: float
    y: float
    z: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def as_list(self) -> list[float]:
        return list(self.as_tuple())


class HomingState(Protocol):
    endstops: Sequence[Endstop[object]]

    def is_homing_z(self) -> bool:
        """Check if the z axis is currently being homed."""
        ...

    def set_z_homed_position(self, position: float) -> None:
        """Set the homed position for the z axis."""
        ...


C = TypeVar("C", covariant=True)


class Endstop(Generic[C], Protocol):
    """Endstop interface for homing operations."""

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
    position: Position | None
    velocity: float | None


S = TypeVar("S", bound=Sample)


class Mcu(Generic[C, S], Protocol):
    def start_homing_scan(self, print_time: float, frequency: float) -> C: ...
    def start_homing_touch(self, print_time: float, threshold: int) -> C: ...
    def stop_homing(self, home_end_time: float) -> float: ...
    def start_session(self, start_condition: Callable[[S], bool] | None = None) -> Session[S]: ...


class MacroParams(Protocol):
    def get(self, name: str, default: str = ...) -> str: ...
    @overload
    def get_float(self, name: str, default: float = ..., *, above: float = ..., minval: float = ...) -> float: ...
    @overload
    def get_float(self, name: str, default: None, *, above: float = ..., minval: float = ...) -> float | None: ...
    def get_int(
        self,
        name: str,
        default: int = ...,
        *,
        minval: int = ...,
        maxval: int = ...,
    ) -> int: ...


P = TypeVar("P", bound=MacroParams, contravariant=True)


class Macro(Generic[P], Protocol):
    name: str
    description: str

    def run(self, params: P) -> None: ...


class ProbeMode(Protocol):
    @property
    def offset(self) -> Position: ...
    @property
    def is_ready(self) -> bool: ...
    def save_z_offset(self, new_offset: float) -> None: ...
    def perform_probe(self) -> float: ...
    def query_is_triggered(self, print_time: float) -> bool: ...


class TemperatureStatus(NamedTuple):
    current: float
    target: float


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

    def move(self, *, x: float = ..., y: float = ..., z: float = ..., speed: float) -> None:
        """Move to requested position."""
        ...

    def is_homed(self, axis: HomingAxis) -> bool:
        """Check if axis is homed."""
        ...

    def get_gcode_z_offset(self) -> float:
        """Returns currently applied gcode offset for the z axis."""
        ...

    def z_homing_move(self, endstop: Endstop[object], *, bottom: float, speed: float) -> float:
        """Starts homing move towards the given endstop."""
        ...

    def set_z_position(self, z: float) -> None:
        """Set the z position of the toolhead."""
        ...

    def get_z_axis_limits(self) -> tuple[float, float]:
        """Get the limits of the z axis."""
        ...

    def manual_probe(self, finalize_callback: Callable[[Position | None], None]) -> None:
        """Start a manual probe."""
        ...

    def clear_z_homing_state(self) -> None:
        """Clears z homing state"""
        ...

    def dwell(self, seconds: float) -> None:
        """Dwell for the given number of seconds."""
        ...

    def get_extruder_temperature(self) -> TemperatureStatus:
        """Get the current and target temperature of the extruder."""
        ...

    def apply_axis_twist_compensation(self, position: Position) -> Position:
        """Apply axis twist compensation to the given position."""
        ...
