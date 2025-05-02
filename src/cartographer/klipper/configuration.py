from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, TypeVar

from typing_extensions import override

from cartographer.configuration import (
    Configuration as CartographerConfiguration,
)
from cartographer.configuration import (
    ScanModelConfiguration,
    ScanModelFit,
    TouchModelConfiguration,
)

if TYPE_CHECKING:
    from configfile import ConfigWrapper


T = TypeVar("T", bound=Enum)


def get_enum_choice(config: ConfigWrapper, option: str, enum_type: type[T], default: T) -> T:
    choice = config.get(option, default.value)
    if choice not in enum_type._value2member_map_:
        msg = f"invalid choice '{choice}' for option '{option}'"
        raise config.error(msg)
    return enum_type(choice)


def get_coordinate_point(config: ConfigWrapper, option: str) -> tuple[float, float]:
    x, y = config.getfloatlist(option, count=2)
    return x, y


class KlipperCartographerConfiguration(CartographerConfiguration):
    def __init__(self, config: ConfigWrapper) -> None:
        self._config: ConfigWrapper = config
        self.x_offset: float = config.getfloat("x_offset")
        self.y_offset: float = config.getfloat("y_offset")
        self.backlash_compensation: float = config.getfloat("backlash_compensation", 0)
        self.move_speed: float = config.getfloat("move_speed", default=50, above=0)
        self.verbose: bool = config.getboolean("verbose", default=False)

        config_name = config.get_name()

        scan_config = config.getsection(f"{config_name} scan")
        # self.scan_samples: int = scan_config.getint("samples", default=20, minval=20)
        self.scan_samples: int = 20
        self.scan_mesh_runs: int = scan_config.getint("mesh_runs", default=1, minval=1)

        touch_config = config.getsection(f"{config_name} touch")
        self.touch_samples: int = touch_config.getint("samples", default=5, minval=3)
        self.touch_max_samples: int = touch_config.getint(
            "max_samples", default=self.touch_samples * 2, minval=self.touch_samples
        )

        self.scan_models: dict[str, ScanModelConfiguration] = {
            cfg.name: cfg
            for cfg in map(
                KlipperScanModelConfiguration.from_config, config.get_prefix_sections(f"{config_name} scan_model")
            )
        }
        self.touch_models: dict[str, TouchModelConfiguration] = {
            cfg.name: cfg
            for cfg in map(
                KlipperTouchModelConfiguration.from_config, config.get_prefix_sections(f"{config_name} touch_model")
            )
        }

        mesh_config = config.getsection("bed_mesh")
        self.scan_speed: float = mesh_config.getfloat("speed", default=50, minval=50)
        self.scan_height: float = mesh_config.getfloat("horizontal_move_z", default=4, minval=1)
        self.zero_reference_position: tuple[float, float] = get_coordinate_point(mesh_config, "zero_reference_position")
        self.mesh_min: tuple[float, float] = get_coordinate_point(mesh_config, "mesh_min")
        self.mesh_max: tuple[float, float] = get_coordinate_point(mesh_config, "mesh_max")

    @override
    def save_new_scan_model(self, name: str, model: ScanModelFit) -> KlipperScanModelConfiguration:
        section_name = f"{self._config.get_name()} scan_model {name}"
        configfile = self._config.get_printer().lookup_object("configfile")
        configfile.set(section_name, "z_offset", 0)
        configfile.set(section_name, "coefficients", ", ".join(map(str, model.coefficients)))
        configfile.set(section_name, "domain", ", ".join(map(str, model.domain)))

        return KlipperScanModelConfiguration(
            self._config.getsection(section_name),
            name=name,
            coefficients=model.coefficients,
            domain=model.domain,
            z_offset=0,
        )

    @override
    def save_new_touch_model(self, name: str, speed: float, threshold: int) -> TouchModelConfiguration:
        section_name = f"{self._config.get_name()} touch_model {name}"
        configfile = self._config.get_printer().lookup_object("configfile")
        configfile.set(section_name, "threshold", threshold)
        configfile.set(section_name, "speed", f"{speed:.1f}")
        configfile.set(section_name, "z_offset", -0.05)

        return KlipperTouchModelConfiguration(
            self._config.getsection(section_name),
            name=name,
            threshold=threshold,
            speed=speed,
            z_offset=0,
        )


class KlipperScanModelConfiguration(ScanModelConfiguration):
    def __init__(
        self,
        config: ConfigWrapper,
        *,
        name: str,
        coefficients: list[float],
        domain: tuple[float, float],
        z_offset: float,
    ) -> None:
        self._config: ConfigWrapper = config
        self.name: str = name
        self.coefficients: list[float] = coefficients
        self.domain: tuple[float, float] = domain
        self.z_offset: float = z_offset

    @override
    def save_z_offset(self, new_offset: float) -> None:
        self._config.get_printer().lookup_object("configfile").set(
            self._config.get_name(), "z_offset", f"{new_offset:.3f}"
        )

    @staticmethod
    def from_config(config: ConfigWrapper) -> KlipperScanModelConfiguration:
        name = config.get_name().split("scan_model", 1)[1].strip()
        coefficients = config.getfloatlist("coefficients")
        domain_raw = config.getfloatlist("domain", count=2)
        domain = (domain_raw[0], domain_raw[1])
        z_offset = config.getfloat("z_offset")

        return KlipperScanModelConfiguration(
            config,
            name=name,
            coefficients=coefficients,
            domain=domain,
            z_offset=z_offset,
        )


class KlipperTouchModelConfiguration(TouchModelConfiguration):
    def __init__(
        self,
        config: ConfigWrapper,
        *,
        name: str,
        threshold: int,
        speed: float,
        z_offset: float,
    ) -> None:
        self._config: ConfigWrapper = config
        self.name: str = name
        self.threshold: int = threshold
        self.speed: float = speed
        self.z_offset: float = z_offset

    @override
    def save_z_offset(self, new_offset: float) -> None:
        self._config.get_printer().lookup_object("configfile").set(
            self._config.get_name(), "z_offset", f"{new_offset:.3f}"
        )

    @staticmethod
    def from_config(config: ConfigWrapper) -> KlipperTouchModelConfiguration:
        name = config.get_name().split("touch_model", 1)[1].strip()
        threshold = config.getint("threshold", minval=1)
        speed = config.getfloat("speed", above=0)
        z_offset = config.getfloat("z_offset", maxval=0)
        return KlipperTouchModelConfiguration(
            config,
            name=name,
            threshold=threshold,
            speed=speed,
            z_offset=z_offset,
        )
