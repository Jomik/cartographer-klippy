# https://github.com/Klipper3d/klipper/blob/master/klippy/kinematics/extruder.py
from typing import final
from extras.heaters import Heater

@final
class Extruder:
    def get_name(self) -> str: ...
    def get_heater(self) -> Heater: ...
