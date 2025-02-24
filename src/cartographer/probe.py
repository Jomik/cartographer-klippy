from __future__ import annotations

from typing import Literal, Tuple, TypedDict, final

from extras.probe import PrinterProbe
from gcode import GCodeCommand
from klippy import Printer
from typing_extensions import Self, override

from cartographer.configuration import CommonConfiguration
from cartographer.scan.endstop import ScanEndstop


class CartographerParams(TypedDict):
    probe_speed: float
    lift_speed: float
    samples: int
    sample_retract_dist: float
    samples_tolerance: float
    samples_tolerance_retries: int
    samples_result: Literal["average", "median"]


class CartographerStatus(TypedDict):
    name: str
    last_query: bool | int
    last_z_result: float


@final
class CartograherPrinterProbe(PrinterProbe):
    def __init__(
        self, config: CommonConfiguration, printer: Printer, endstop: ScanEndstop
    ) -> None:
        self._config = config
        self._printer = printer
        self._endstop = endstop
        self._results: list[list[float]] = []
        self._has_session = False

    @override
    def get_probe_params(self, gcmd: GCodeCommand | None = None) -> CartographerParams:
        if gcmd is None:
            gcmd = self._printer.lookup_object("gcode").create_gcode_command("", "", {})
        probe_speed = gcmd.get_float("PROBE_SPEED", 5, above=0.0)
        lift_speed = gcmd.get_float("LIFT_SPEED", probe_speed, above=0.0)
        samples = gcmd.get_int("SAMPLES", 10, minval=1)
        sample_retract_dist = gcmd.get_float("SAMPLE_RETRACT_DIST", 0.0, above=0.0)
        samples_tolerance = gcmd.get_float("SAMPLES_TOLERANCE", 0.001, minval=0.0)
        samples_retries = gcmd.get_int("SAMPLES_TOLERANCE_RETRIES", 3, minval=0)

        return {
            "probe_speed": probe_speed,
            "lift_speed": lift_speed,
            "samples": samples,
            "sample_retract_dist": sample_retract_dist,
            "samples_tolerance": samples_tolerance,
            "samples_tolerance_retries": samples_retries,
            "samples_result": "median",
        }

    @override
    def get_offsets(self) -> Tuple[float, float, float]:
        return (
            self._config.x_offset,
            self._config.y_offset,
            self._endstop.get_position_endstop(),
        )

    @override
    def get_status(self, eventtime: float) -> CartographerStatus:
        # TODO: Actually get real status
        return {
            "name": "cartographer",
            "last_query": 0,
            "last_z_result": 2.0,
        }

    def _probe_state_error(self):
        raise self._printer.command_error(
            "Internal probe error - start/end probe session mismatch"
        )

    @override
    def start_probe_session(self, gcmd: GCodeCommand) -> Self:
        if self._has_session:
            self._probe_state_error()
        self._has_session = True
        return self

    def run_probe(self, gcmd: GCodeCommand) -> None:
        params = self.get_probe_params(gcmd)
        self._results.append(
            self._endstop.probe(params["probe_speed"], params["samples"])
        )

    def end_probe_session(self) -> None:
        if not self._has_session:
            self._probe_state_error()
        self._has_session = False

    def pull_probed_results(self) -> list[list[float]]:
        results = self._results
        self._results = []
        return results
