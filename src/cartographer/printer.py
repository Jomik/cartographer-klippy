from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Literal, Protocol, TypedDict, TypeVar

if TYPE_CHECKING:
    from collections.abc import Sequence

HomingAxis = Literal["x", "y", "z"]


class Position(TypedDict):
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


C = TypeVar("C", covariant=True)


class Endstop(Protocol, Generic[C]):
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
