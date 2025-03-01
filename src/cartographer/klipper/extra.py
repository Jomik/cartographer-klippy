from __future__ import annotations

from typing import final

from configfile import ConfigWrapper

from cartographer.endstop import Endstop
from cartographer.modes.none_mode import NoneMode

from .endstop import EndstopWrapper
from .mcu import KlipperCartographerMcu


def load_config(config: ConfigWrapper):
    return PrinterCartographer(config)


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper) -> None:
        mcu = KlipperCartographerMcu(config)
        endstop = Endstop(mcu, NoneMode())
        _ = EndstopWrapper(mcu, endstop)
