from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.config.parser import (
    ParseConfigWrapper,
    parse_bed_mesh_config,
    parse_general_config,
    parse_scan_config,
    parse_scan_model_config,
    parse_touch_config,
    parse_touch_model_config,
)
from cartographer.interfaces.configuration import (
    Configuration,
    ScanModelConfiguration,
    TouchModelConfiguration,
)

if TYPE_CHECKING:
    from configfile import ConfigWrapper


@final
class KlipperConfigWrapper(ParseConfigWrapper):
    def __init__(self, config: ConfigWrapper, section_prefix: str = "") -> None:
        self._config = config
        self._section_prefix = section_prefix

    @override
    def get_name(self) -> str:
        return self._config.get_name().split(" ")[-1]

    @override
    def get_str(self, option: str, default: str) -> str:
        return self._config.get(option, default=default)

    @override
    def get_optional_str(self, option: str) -> str | None:
        return self._config.get(option, default=None)

    @override
    def get_float(
        self, option: str, default: float, minimum: float | None = None, maximum: float | None = None
    ) -> float:
        return self._config.getfloat(option, default=default, minval=minimum, maxval=maximum)

    @override
    def get_required_float(self, option: str) -> float:
        return self._config.getfloat(option)

    @override
    def get_required_float_list(self, option: str, count: int | None = None) -> list[float]:
        return self._config.getfloatlist(option, count=count)

    @override
    def get_int(self, option: str, default: int) -> int:
        return self._config.getint(option, default=default)

    @override
    def get_required_int_list(self, option: str, count: int | None = None) -> list[int]:
        return self._config.getintlist(option, count=count)

    @override
    def get_bool(self, option: str, default: bool) -> bool:
        return self._config.getboolean(option, default=default)


@final
class KlipperConfiguration(Configuration):
    def __init__(self, config: ConfigWrapper) -> None:
        self.wrapper = config
        self._config = config.get_printer().lookup_object("configfile")

        self.name = config.get_name()

        self.general = parse_general_config(KlipperConfigWrapper(config))
        self.bed_mesh = parse_bed_mesh_config(KlipperConfigWrapper(config.getsection("bed_mesh")))

        self.scan_model_prefix = f"{self.name} scan_model"
        scan_models = {
            cfg.get_name(): parse_scan_model_config(cfg)
            for cfg in (KlipperConfigWrapper(wrapper) for wrapper in config.get_prefix_sections(self.scan_model_prefix))
        }
        self.scan = parse_scan_config(KlipperConfigWrapper(config.getsection(f"{self.name} scan")), scan_models)

        self.touch_model_prefix = f"{self.name} touch_model"
        touch_models = {
            cfg.get_name(): parse_touch_model_config(cfg)
            for cfg in (
                KlipperConfigWrapper(wrapper) for wrapper in config.get_prefix_sections(self.touch_model_prefix)
            )
        }
        self.touch = parse_touch_config(KlipperConfigWrapper(config.getsection(f"{self.name} touch")), touch_models)

    @override
    def save_scan_model(self, config: ScanModelConfiguration) -> None:
        save = partial(self._config.set, f"{self.scan_model_prefix} {config.name}")
        save("coefficients", ",".join(map(str, config.coefficients)))
        save("domain", ",".join(map(str, config.domain)))
        save("z_offset", config.z_offset)
        self.scan.models[config.name] = config

    @override
    def save_touch_model(self, config: TouchModelConfiguration) -> None:
        save = partial(self._config.set, f"{self.touch_model_prefix} {config.name}")
        save("threshold", config.threshold)
        save("speed", config.speed)
        save("z_offset", config.z_offset)
        self.touch.models[config.name] = config

    @override
    def save_z_backlash(self, backlash: float) -> None:
        self._config.set(self.name, "z_backlash", backlash)
