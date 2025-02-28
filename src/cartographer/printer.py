from __future__ import annotations

from typing import Literal, NamedTuple, Protocol

HomingAxis = Literal["x", "y", "z"]


class Position(NamedTuple):
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
    def get_last_move_time(self) -> float: ...
    def wait_moves(self) -> None: ...
