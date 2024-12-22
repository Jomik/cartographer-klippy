from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, final

from configfile import ConfigWrapper
from configfile import error as ConfigError
from klippy import Printer
from mcu import MCU, MCU_endstop, MCU_trsync, TriggerDispatch
from numpy.polynomial import Polynomial
from reactor import ReactorCompletion
from stepper import MCU_stepper
from typing_extensions import override

from cartographer.mcu.helper import McuHelper, RawSample
from cartographer.mcu.stream import StreamHandler
from cartographer.wrappers import polynomial

MODEL_PREFIX = "cartographer scan_model "
TRIGGER_DISTANCE = 2.0


@final
class ScanEndstop(MCU_endstop):
    def __init__(
        self,
        mcu_helper: McuHelper,
        model: ScanModel,
    ):
        self._mcu_helper = mcu_helper
        self._stream_handler = StreamHandler(
            mcu_helper.get_mcu().get_printer(), mcu_helper
        )
        self._mcu = mcu_helper.get_mcu()
        self._dispatch = TriggerDispatch(self._mcu)
        self._model = model

    @override
    def get_mcu(self) -> MCU:
        return self._mcu

    @override
    def add_stepper(self, stepper: MCU_stepper) -> None:
        self._dispatch.add_stepper(stepper)

    @override
    def get_steppers(self) -> list[MCU_stepper]:
        return self._dispatch.get_steppers()

    @override
    def home_start(
        self,
        print_time: float,
        sample_time: float,
        sample_count: int,
        rest_time: float,
        triggered: bool = True,
    ) -> ReactorCompletion[bool]:
        self._mcu_helper.set_threshold(
            self._model.distance_to_frequency(TRIGGER_DISTANCE)
        )
        trigger_completion = self._dispatch.start(print_time)
        self._mcu.get_printer().lookup_object("toolhead").wait_moves()
        self._mcu_helper.home_scan(self._dispatch.get_oid())
        return trigger_completion

    @override
    def home_wait(self, home_end_time: float) -> float:
        self._dispatch.wait_end(home_end_time)
        self._mcu_helper.stop_home()
        res = self._dispatch.stop()
        if res >= MCU_trsync.REASON_COMMS_TIMEOUT:
            raise self._mcu.get_printer().command_error(
                "Communication timeout during homing"
            )
        if res != MCU_trsync.REASON_ENDSTOP_HIT:
            return 0.0
        if self._mcu.is_fileoutput():
            return home_end_time
        # TODO: Use a query state command for actual end time
        return home_end_time

    def _get_sample(self) -> Optional[RawSample]:
        sample: Optional[RawSample] = None

        def callback(data: RawSample) -> bool:
            nonlocal sample
            sample = data
            return True

        with self._stream_handler.session(callback) as session:
            session.wait()

        return sample

    @override
    def query_endstop(self, print_time: float) -> int:
        # TODO: Use a query state command for actual state
        sample = self._get_sample()

        if sample is None:
            return 0

        if (
            self._model.frequency_to_distance(
                self._mcu_helper.count_to_frequency(sample["data"])
            )
            < TRIGGER_DISTANCE
        ):
            return 1
        return 0


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
