from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from extras.probe import PrinterProbe
from typing_extensions import override

from cartographer.klipper.utils import reraise_as_command_error

if TYPE_CHECKING:
    from gcode import GCodeCommand

    from cartographer.macros.probe import ProbeMacro, QueryProbeMacro
    from cartographer.printer_interface import ProbeMode


class ProbeStatus(TypedDict):
    name: str
    last_query: int
    last_z_result: float


class ProbeParams(TypedDict):
    probe_speed: float
    lift_speed: float


# TODO: Get the values from some configuration?
DEFAULT_LIFT_SPEED = 10
DEFAULT_PROBE_SPEED = 3


class KlipperProbeSession:
    def __init__(self, probe: ProbeMode) -> None:
        self.probe: ProbeMode = probe
        self.positions: list[list[float]] = []

    @reraise_as_command_error
    def run_probe(self, gcmd: GCodeCommand) -> None:
        del gcmd
        distance = self.probe.perform_probe()
        self.positions.append([0, 0, distance])

    def pull_probed_results(self):
        return self.positions

    def end_probe_session(self) -> None:
        pass


class KlipperCartographerProbe(PrinterProbe):
    def __init__(
        self,
        probe: ProbeMode,
        probe_macro: ProbeMacro,
        query_probe_macro: QueryProbeMacro,
    ) -> None:
        self.probe: ProbeMode = probe
        self.probe_macro: ProbeMacro = probe_macro
        self.query_probe_macro: QueryProbeMacro = query_probe_macro

    @override
    def get_probe_params(self, gcmd: GCodeCommand | None = None) -> ProbeParams:
        if gcmd is None:
            return ProbeParams(lift_speed=DEFAULT_LIFT_SPEED, probe_speed=DEFAULT_PROBE_SPEED)

        lift_speed = gcmd.get_float("LIFT_SPEED", default=DEFAULT_LIFT_SPEED, above=0)
        probe_speed = gcmd.get_float("SPEED", default=DEFAULT_PROBE_SPEED, above=0)
        return ProbeParams(lift_speed=lift_speed, probe_speed=probe_speed)

    @override
    def get_offsets(self) -> tuple[float, float, float]:
        return self.probe.offset.as_tuple()

    @override
    def get_status(self, eventtime: float) -> ProbeStatus:
        return ProbeStatus(
            name="cartographer",
            last_query=1 if self.query_probe_macro.last_triggered else 0,
            last_z_result=self.probe_macro.last_distance,
        )

    @override
    def start_probe_session(self, gcmd: GCodeCommand) -> KlipperProbeSession:
        return KlipperProbeSession(self.probe)
