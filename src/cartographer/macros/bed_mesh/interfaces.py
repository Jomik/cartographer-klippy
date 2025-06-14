from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Protocol

from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from cartographer.interfaces.printer import Position

Point: TypeAlias = "tuple[float, float]"


class PathPlanner(Protocol):
    def generate_path(self, points: list[Point]) -> Iterator[Point]: ...


class BedMeshAdapter(Protocol):
    def apply_mesh(self, mesh_points: list[Position], profile_name: str | None = None): ...
