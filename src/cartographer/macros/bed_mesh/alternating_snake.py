from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Literal, final

from typing_extensions import override

from cartographer.macros.bed_mesh.interfaces import PathGenerator
from cartographer.macros.bed_mesh.snake_path import SnakePathGenerator

if TYPE_CHECKING:
    from cartographer.macros.bed_mesh.interfaces import Point


@final
class AlternatingSnakePathGenerator(PathGenerator):
    def __init__(self, main_direction: Literal["x", "y"], corner_radius: float):
        self.main_direction: Literal["x", "y"] = main_direction
        self.corner_radius = corner_radius

    @override
    def generate_path(self, points: list[Point]) -> Iterator[Point]:
        alternate_direction = "y" if self.main_direction == "x" else "x"
        main_path = SnakePathGenerator(self.main_direction, self.corner_radius)
        alternate_path = SnakePathGenerator(alternate_direction, self.corner_radius)
        yield from main_path.generate_path(points)
        yield from reversed(list(alternate_path.generate_path(points)))
