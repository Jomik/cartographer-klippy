# https://github.com/Klipper3d/klipper/blob/master/klippy/extras/temperature_sensor.py

from typing import Protocol, TypedDict

class _Status(TypedDict):
    temperature: float
    measured_min_temp: float
    measured_max_temp: float

class PrinterSensorGeneric(Protocol):
    def get_temp(self, eventtime: float) -> tuple[float, float]: ...
    def get_status(self, eventtime: float) -> _Status: ...
