from __future__ import annotations

from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.macros.bed_mesh.interfaces import BedMeshAdapter

if TYPE_CHECKING:
    from configfile import ConfigWrapper

    from cartographer.macros.bed_mesh.interfaces import HeightMatrix


@final
class KlipperBedMesh(BedMeshAdapter):
    def __init__(self, config: ConfigWrapper) -> None:
        self.config = config.getsection("bed_mesh")
        self.bed_mesh = config.get_printer().load_object(self.config, "bed_mesh")

    @override
    def apply_mesh(self, matrix: HeightMatrix, profile_name: str | None = None):
        pass
