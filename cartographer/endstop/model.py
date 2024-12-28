from __future__ import annotations

from dataclasses import dataclass

from configfile import ConfigWrapper
from configfile import error as ConfigError
from klippy import Printer
from numpy.polynomial import Polynomial

from cartographer.helpers import polynomial

MODEL_PREFIX = "cartographer scan_model "
TRIGGER_DISTANCE = 2.0


@dataclass
class ScanModel:
    printer: Printer
    name: str
    poly: Polynomial
    temperature: float
    min_z: float
    max_z: float

    @staticmethod
    def load(config: ConfigWrapper, name: str) -> ScanModel:
        if not config.has_section(MODEL_PREFIX + name):
            raise config.printer.command_error(f"Model {name} not found")

        config = config.getsection(MODEL_PREFIX + name)
        printer = config.get_printer()

        temperature = config.getfloat("temperature")
        coefficients = config.getfloatlist("coefficients")
        domain = config.getfloatlist("domain", count=2)
        min_z, max_z = config.getfloatlist("z_range", count=2)

        poly = Polynomial(coefficients, domain)

        return ScanModel(printer, name, poly, temperature, min_z, max_z)

    def save(self) -> None:
        configfile = self.printer.lookup_object("configfile")
        section = MODEL_PREFIX + self.name

        try:
            result = polynomial.to_strings(self.poly)
            coefficients = result["coefficients"]
            domain = result["domain"]
        except ValueError as e:
            raise ConfigError(f"Failed to save model {self.name}: {e}")

        config_data = {
            "temperature": self.temperature,
            "coefficients": coefficients,
            "domain": domain,
            "z_range": f"{self.min_z}, {self.max_z}",
        }

        for key, value in config_data.items():
            configfile.set(section, key, value)

    def frequency_to_distance(self, frequency: float) -> float:
        # TODO: Temperature compensation

        domain = polynomial.get_domain(self.poly)
        if domain is None:
            raise self.printer.command_error("Model is missing domain")

        begin, end = domain
        inverse_frequency = 1 / frequency

        if inverse_frequency > end:
            return float("inf")
        elif inverse_frequency < begin:
            return float("-inf")

        return float(polynomial.evaluate(self.poly, inverse_frequency))

    def distance_to_frequency(self, distance: float, max_e: float = 1e-8) -> float:
        if distance < self.min_z or distance > self.max_z:
            raise self.printer.command_error(
                f"Attempted to map out-of-range distance {distance:.3f}, valid range [{self.min_z:.3f}, {self.max_z:.3f}]"
            )

        # TODO: Temperature compensation

        domain = polynomial.get_domain(self.poly)
        if domain is None:
            raise self.printer.command_error("Model is missing domain")

        begin, end = domain

        for _ in range(50):
            mid = (end + begin) / 2
            value = polynomial.evaluate(self.poly, mid)

            if abs(value - distance) < max_e:
                return float(1.0 / mid)
            elif value < distance:
                begin = mid
            else:
                end = mid

        raise self.printer.command_error("Calibration model convergence error")
