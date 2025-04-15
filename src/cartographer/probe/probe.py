from __future__ import annotations

from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from cartographer.printer_interface import C, S
    from cartographer.probe.scan_mode import ScanMode
    from cartographer.probe.touch_mode import TouchMode


@final
class Probe:
    """Main probe class managing mode instances"""

    def __init__(self, scan: ScanMode[C, S], touch: TouchMode[C]):
        self.scan = scan
        self.touch = touch

    def query_is_triggered(self) -> bool:
        return self.scan.query_is_triggered()

    def perform_scan(self) -> float:
        return self.scan.perform_probe()

    def perform_touch(self) -> float:
        return self.touch.perform_probe()
