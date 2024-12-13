# https://github.com/Klipper3d/klipper/blob/master/klippy/klippy.py
from typing import Callable, Literal, TypeVar, overload

import configfile
from extras.bed_mesh import BedMesh
from extras.heaters import PrinterHeaters
from extras.homing import Homing, PrinterHoming
from extras.probe import PrinterProbe
from configfile import ConfigWrapper, PrinterConfig, sentinel
from gcode import CommandError, GCodeDispatch
from pins import PrinterPins
from reactor import Reactor
from stepper import PrinterRail
from toolhead import ToolHead

from cartographer.scanner import PrinterScanner

T = TypeVar("T")

class Printer:
    config_error: type[configfile.error]
    command_error: type[CommandError]
    def add_object(self, name: Literal["probe"], obj: PrinterProbe) -> None: ...
    @overload
    def load_object(
        self,
        config: ConfigWrapper,
        section: Literal["bed_mesh"],
    ) -> BedMesh: ...
    @overload
    def load_object(
        self,
        config: ConfigWrapper,
        section: Literal["heaters"],
    ) -> PrinterHeaters: ...
    @overload
    def load_object(
        self,
        config: ConfigWrapper,
        section: str,
        default: T | type[sentinel] = sentinel,
    ) -> T: ...
    def is_shutdown(self) -> bool: ...
    def invoke_shutdown(self, msg: str) -> None: ...
    def get_reactor(self) -> Reactor: ...
    @overload
    def register_event_handler(
        self, event: Literal["klippy:connect"], callback: Callable[[], None]
    ) -> None: ...
    @overload
    def register_event_handler(
        self, event: Literal["klippy:disconnect"], callback: Callable[[], None]
    ) -> None: ...
    @overload
    def register_event_handler(
        self, event: Literal["klippy:shutdown"], callback: Callable[[], None]
    ) -> None: ...
    @overload
    def register_event_handler(
        self, event: Literal["klippy:mcu_identify"], callback: Callable[[], None]
    ) -> None: ...
    @overload
    def register_event_handler(
        self,
        event: Literal["homing:home_rails_begin"],
        callback: Callable[[Homing, list[PrinterRail]], None],
    ) -> None: ...
    @overload
    def register_event_handler(
        self,
        event: Literal["homing:home_rails_end"],
        callback: Callable[[Homing, list[PrinterRail]], None],
    ) -> None: ...
    @overload
    def lookup_object(self, name: Literal["configfile"]) -> PrinterConfig: ...
    @overload
    def lookup_object(self, name: Literal["gcode"]) -> GCodeDispatch: ...
    @overload
    def lookup_object(self, name: Literal["homing"]) -> PrinterHoming: ...
    @overload
    def lookup_object(self, name: Literal["pins"]) -> PrinterPins: ...
    @overload
    def lookup_object(self, name: Literal["scanner"]) -> PrinterScanner: ...
    @overload
    def lookup_object(self, name: Literal["toolhead"]) -> ToolHead: ...
    @overload
    def lookup_object(self, name: str, default: T | type[sentinel] = sentinel) -> T: ...
