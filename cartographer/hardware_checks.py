import logging
from typing import Optional, final

from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import Sample

logger = logging.getLogger(__name__)

SHORTED_FREQUENCY_VALUE = 0xFFFFFFF
FREQUENCY_RANGE_PERCENT = 1.35


@final
class HardwareObserver:
    __min_frequency: Optional[float] = None

    @property
    def _min_frequency(self) -> float:
        if self.__min_frequency is not None:
            return self.__min_frequency
        base = self._mcu_helper.query_base()
        self.__min_frequency = self._mcu_helper.count_to_frequency(base.f_count)
        return self.__min_frequency

    def __init__(self, mcu_helper: McuHelper):
        self._mcu_helper = mcu_helper
        self._printer = mcu_helper.get_printer()
        self._printer.register_event_handler(
            "klippy:mcu_identify", self._handle_mcu_identify
        )

    def _handle_mcu_identify(self) -> None:
        carto = self._printer.lookup_object("cartographer")
        stream_handler = carto.get_stream_handler()

        _ = stream_handler.session(self._sample_callback, active=False)

    def _sample_callback(self, sample: Sample) -> bool:
        if sample.count == SHORTED_FREQUENCY_VALUE:
            self._handle_hardware_failure("coil is shorted or not connected")
        elif sample.frequency > FREQUENCY_RANGE_PERCENT * self._min_frequency:
            self._handle_hardware_failure(
                "coil frequency reeding exceeded max expected value"
            )

        return False

    def _handle_hardware_failure(self, issue: str) -> None:
        logger.error(issue)
        if self._mcu_helper.is_streaming():
            self._printer.invoke_shutdown(issue)
            return

        gcode = self._printer.lookup_object("gcode")
        gcode.respond_raw(f"!! {issue}\n")
