from __future__ import annotations

from typing import Generic, Literal, Protocol, TypeVar, overload

HomingAxis = Literal["x", "y", "z"]


class HomingState(Protocol):
    def get_axes(self) -> list[HomingAxis]:
        """Get the axes currently being homed."""
        ...

    def set_homed_position(self, axis: HomingAxis, position: float) -> None:
        """Set the homed position for the given axis."""
        ...


T = TypeVar("T")


class TriggerDispatch(Protocol):
    def get_oid(self) -> int: ...
    def start(self, print_time: float) -> ReactorCompletion[bool | int]: ...
    def wait_end(self, end_time: float) -> None: ...
    def stop(self) -> int: ...


class ReactorCompletion(Protocol, Generic[T]):
    def test(self) -> bool: ...
    def complete(self, result: bool | int) -> None: ...
    @overload
    def wait(self, waketime: float, waketime_result: T) -> T: ...
    @overload
    def wait(self) -> T | None: ...
