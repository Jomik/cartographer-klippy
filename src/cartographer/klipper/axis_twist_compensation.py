from __future__ import annotations

from typing import TYPE_CHECKING, Literal, final

from typing_extensions import override

from cartographer.macros.axis_twist_compensation import AxisTwistCompensationHelper, CalibrationOptions

if TYPE_CHECKING:
    from configfile import ConfigWrapper


@final
class KlipperAxisTwistCompensationHelper(AxisTwistCompensationHelper):
    def __init__(self, config: ConfigWrapper) -> None:
        self.config = config.getsection("axis_twist_compensation")
        self.compensation = config.get_printer().load_object(self.config, "axis_twist_compensation")
        self.move_height = self.compensation.horizontal_move_z
        self.speed = self.compensation.speed

    @override
    def clear_compensations(self, axis: Literal["x", "y"]) -> None:
        self.compensation.clear_compensations(axis.upper())

    @override
    def save_compensations(self, axis: Literal["x", "y"], start: float, end: float, values: list[float]) -> None:
        configfile = self.config.get_printer().lookup_object("configfile")
        configname = self.config.get_name()
        values_as_str = ", ".join([f"{x:.6f}" for x in values])

        if axis == "x":
            configfile.set(configname, "z_compensations", values_as_str)
            configfile.set(configname, "compensation_start_x", start)
            configfile.set(configname, "compensation_end_x", end)

            self.compensation.z_compensations = values
            self.compensation.compensation_start_x = start
            self.compensation.compensation_end_x = end
        elif axis == "y":
            configfile.set(configname, "zy_compensations", values_as_str)
            configfile.set(configname, "compensation_start_y", start)
            configfile.set(configname, "compensation_end_y", end)

            self.compensation.zy_compensations = values
            self.compensation.compensation_start_y = start
            self.compensation.compensation_end_y = end

    @override
    def get_calibration_options(self, axis: Literal["x", "y"]) -> CalibrationOptions:
        if axis == "x":
            return CalibrationOptions(
                self.compensation.calibrate_start_x,
                self.compensation.calibrate_end_x,
                self.compensation.calibrate_y,
            )
        elif axis == "y":
            return CalibrationOptions(
                self.compensation.calibrate_start_y,
                self.compensation.calibrate_end_y,
                self.compensation.calibrate_x,
            )
