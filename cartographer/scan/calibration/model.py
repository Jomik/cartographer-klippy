from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from configfile import ConfigWrapper
from configfile import error as ConfigError
from klippy import Printer
from numpy.polynomial import Polynomial

from cartographer.scan.calibration.stream import CalibrationSample
from cartographer.helpers import numpy as numpy_helper
from cartographer.helpers.strings import format_macro

MODEL_PREFIX = "cartographer scan_model "
TRIGGER_DISTANCE = 2.0


@dataclass
class Model:
    printer: Printer
    name: str
    poly: Polynomial
    temperature: float
    min_z: float
    max_z: float

    @staticmethod
    def load(config: ConfigWrapper, name: str) -> Model:
        if not config.has_section(MODEL_PREFIX + name):
            raise config.printer.command_error(f"Model {name} not found")

        config = config.getsection(MODEL_PREFIX + name)
        printer = config.get_printer()

        temperature = config.getfloat("temperature")
        coefficients = config.getfloatlist("coefficients")
        domain = config.getfloatlist("domain", count=2)
        min_z, max_z = config.getfloatlist("z_range", count=2)

        poly = Polynomial(coefficients, domain)

        return Model(printer, name, poly, temperature, min_z, max_z)

    @staticmethod
    def fit(printer: Printer, name: str, samples: list[CalibrationSample]) -> Model:
        z_offsets = [sample.position[2] for sample in samples]
        frequencies = [sample.frequency for sample in samples]
        temperatures = [sample.temperature for sample in samples]
        inv_frequencies = [1 / freq for freq in frequencies]

        poly = numpy_helper.fit(inv_frequencies, z_offsets, degrees=9)
        temp_median = float(np.median(temperatures))

        return Model(printer, name, poly, temp_median, min(z_offsets), max(z_offsets))

    def save(self) -> None:
        configfile = self.printer.lookup_object("configfile")
        section = MODEL_PREFIX + self.name

        try:
            result = numpy_helper.to_strings(self.poly)
            coefficients = result["coefficients"]
            domain = result["domain"]
        except ValueError as e:
            raise ConfigError(f"Failed to save model {self.name}: {e}")

        config_data = {
            "temperature": self.temperature,
            "coefficients": coefficients,
            "domain": domain,
            "z_range": numpy_helper.array2string(np.array([self.min_z, self.max_z])),
        }

        for key, value in config_data.items():
            configfile.set(section, key, value)

        self.printer.lookup_object("gcode").respond_info(
            f"Calibration model {self.name} has been updated."
            + f"\nPlease run the {format_macro('SAVE_CONFIG')} macro to update the printer configuration and restart the printer."
        )

    def frequency_to_distance(self, frequency: float) -> float:
        # TODO: Temperature compensation

        domain = numpy_helper.get_domain(self.poly)
        if domain is None:
            raise self.printer.command_error("Model is missing domain")

        begin, end = domain
        inverse_frequency = 1 / frequency

        if inverse_frequency > end:
            return float("inf")
        elif inverse_frequency < begin:
            return float("-inf")

        return float(numpy_helper.evaluate(self.poly, inverse_frequency))

    def distance_to_frequency(self, distance: float, max_e: float = 1e-8) -> float:
        if distance < self.min_z or distance > self.max_z:
            raise self.printer.command_error(
                f"Attempted to map out-of-range distance {distance:.3f}, valid range [{self.min_z:.3f}, {self.max_z:.3f}]"
            )

        # TODO: Temperature compensation

        domain = numpy_helper.get_domain(self.poly)
        if domain is None:
            raise self.printer.command_error("Model is missing domain")

        begin, end = domain

        for _ in range(50):
            mid = (end + begin) / 2
            value = numpy_helper.evaluate(self.poly, mid)

            if abs(value - distance) < max_e:
                return float(1.0 / mid)
            elif value < distance:
                begin = mid
            else:
                end = mid

        raise self.printer.command_error("Calibration model convergence error")
