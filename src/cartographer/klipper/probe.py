from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypedDict

from extras.probe import PrinterProbe
from typing_extensions import override

if TYPE_CHECKING:
    from gcode import GCodeCommand

    from cartographer.macros.probe import ProbeMacro, QueryProbeMacro
    from cartographer.printer_interface import Probe


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
    def __init__(self, probe: Probe) -> None:
        self.probe: Probe = probe
        self.positions: list[list[float]] = []

    def run_probe(self, gcmd: GCodeCommand) -> None:
        # TODO: Consolidate with below get_probe_params
        probe_speed = gcmd.get_float("SPEED", default=DEFAULT_PROBE_SPEED, above=0)
        distance = self.probe.probe(speed=probe_speed)
        self.positions.append([0, 0, distance])

    def pull_probed_results(self):
        return self.positions

    def end_probe_session(self) -> None:
        pass


class Configuration(Protocol):
    x_offset: float
    y_offset: float


class KlipperCartographerProbe(PrinterProbe):
    def __init__(
        self,
        probe: Probe,
        config: Configuration,
        probe_macro: ProbeMacro,
        query_probe_macro: QueryProbeMacro,
    ) -> None:
        self.probe: Probe = probe
        self.config: Configuration = config
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
        return (self.config.x_offset, self.config.y_offset, self.probe.z_offset)

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
