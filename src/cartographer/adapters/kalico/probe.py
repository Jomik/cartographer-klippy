from __future__ import annotations

from typing import TYPE_CHECKING, final

from gcode import CommandError, GCodeCommand
from typing_extensions import override

from cartographer.adapters.klipper.probe import KlipperCartographerProbe, KlipperProbeSession
from cartographer.adapters.utils import reraise_as

if TYPE_CHECKING:
    from cartographer.adapters.klipper.toolhead import KlipperToolhead
    from cartographer.interfaces.printer import ProbeMode
    from cartographer.macros.probe import ProbeMacro, QueryProbeMacro


@final
class KalicoCartographerProbe(KlipperCartographerProbe):
    def __init__(
        self,
        toolhead: KlipperToolhead,
        probe: ProbeMode,
        probe_macro: ProbeMacro,
        query_probe_macro: QueryProbeMacro,
    ) -> None:
        super().__init__(toolhead, probe, probe_macro, query_probe_macro)
        self.sample_count = 1
        self.samples_tolerance = 0.1
        self.samples_retries = 0
        self._probe_session = KlipperProbeSession(probe, toolhead)

    def multi_probe_begin(self):
        pass

    def multi_probe_end(self):
        pass

    @override
    def start_probe_session(self, gcmd: GCodeCommand) -> KlipperProbeSession:
        return self._probe_session

    @reraise_as(CommandError)
    def run_probe(self, gcmd: GCodeCommand) -> None:
        return self._probe_session.run_probe(gcmd)

    def pull_probed_results(self):
        return self._probe_session.pull_probed_results()

    def end_probe_session(self) -> None:
        return self._probe_session.end_probe_session()
