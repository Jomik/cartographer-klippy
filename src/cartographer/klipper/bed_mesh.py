from __future__ import annotations

from typing import TYPE_CHECKING, final

from extras.bed_mesh import BedMeshError
from gcode import GCodeCommand, GCodeDispatch
from typing_extensions import override

from cartographer.macros.bed_mesh import MeshHelper, MeshPoint

if TYPE_CHECKING:
    from configfile import ConfigWrapper

    from cartographer.printer_interface import Position


@final
class KlipperMeshHelper(MeshHelper[GCodeCommand]):
    def __init__(self, config: ConfigWrapper, gcode: GCodeDispatch) -> None:
        mesh_config = config.getsection("bed_mesh")
        self._bed_mesh = config.get_printer().load_object(mesh_config, "bed_mesh")
        # Loading "bed_mesh" above registers the command.
        self.macro = gcode.register_command("BED_MESH_CALIBRATE", None)

    @override
    def orig_macro(self, params: GCodeCommand) -> None:
        if self.macro is not None:
            self.macro(params)

    @override
    def prepare(self, params: GCodeCommand) -> None:
        profile_name = params.get("PROFILE", "default")
        if not profile_name.strip():
            msg = "value for parameter 'PROFILE' must be specified"
            raise RuntimeError(msg)
        self._bed_mesh.set_mesh(None)
        self._bed_mesh.bmc._profile_name = profile_name
        try:
            self._bed_mesh.bmc.update_config(params)
        except BedMeshError as e:
            raise RuntimeError(str(e)) from e

    @override
    def generate_path(self) -> list[MeshPoint]:
        path = self._bed_mesh.bmc.probe_mgr.iter_rapid_path()
        return [MeshPoint(p[0], p[1], include) for (p, include) in path]

    @override
    def finalize(self, offset: Position, positions: list[Position]):
        self._bed_mesh.bmc.probe_finalize(
            [offset.x, offset.y, offset.z],
            [[p.x, p.y, p.z] for p in positions],
        )
