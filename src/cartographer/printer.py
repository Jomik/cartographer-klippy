from __future__ import annotations

from typing import Literal, Protocol, TypedDict

HomingAxis = Literal["x", "y", "z"]


class Position(TypedDict):
    x: float
    y: float
    z: float


class HomingState(Protocol):
    def is_homing(self, axis: HomingAxis) -> bool:
        """Check if axis is currently being homed."""
        ...

    def set_homed_position(self, axis: HomingAxis, position: float) -> None:
        """Set the homed position for the given axis."""
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


class Endstop(Protocol):
    def query_is_triggered(self, print_time: float) -> int:
        """Return true if endstop is currently triggered"""
        ...

    def home_start(self, print_time: float) -> object:
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
