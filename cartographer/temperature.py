import logging
from typing import Callable, final

from configfile import ConfigWrapper

from cartographer.mcu.stream import Sample

REPORT_TIME = 0.300

logger = logging.getLogger(__name__)


@final
class PrinterTemperatureCoil:
    def __init__(self, config: ConfigWrapper):
        self._printer = config.get_printer()
        self._name = config.get_name()
        self._min_temp = 0.0
        self._max_temp = 0.0
        self._temperature_callback = None
        self._printer.register_event_handler(
            "klippy:mcu_identify", self._handle_mcu_identify
        )

    def _handle_mcu_identify(self) -> None:
        carto = self._printer.lookup_object("cartographer")
        stream_handler = carto.get_stream_handler()
        _ = stream_handler.session(self._sample_callback, active=False)

    def setup_callback(
        self, temperature_callback: Callable[[float, float], None]
    ) -> None:
        self._temperature_callback = temperature_callback

    def get_report_time_delta(self) -> float:
        return REPORT_TIME

    def setup_minmax(self, min_temp: float, max_temp: float) -> None:
        self._min_temp = min_temp
        self._max_temp = max_temp

    def _sample_callback(self, sample: Sample) -> bool:
        if self._temperature_callback is None:
            return False
        self._temperature_callback(sample.time, sample.temperature)
        if not (self._min_temp <= sample.temperature <= self._max_temp):
            logger.warning(
                f"Temperature for {self._name} at {sample.temperature} is out of range "
                + f"({self._min_temp} - {self._max_temp})"
            )

        return False
