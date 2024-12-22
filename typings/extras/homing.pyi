# https://github.com/Klipper3d/klipper/blob/master/klippy/extras/homing.py

type _Pos = list[float]

class PrinterHoming:
    def probing_move(self, mcu_probe: object, pos: _Pos, speed: float) -> _Pos: ...

class Homing:
    def set_homed_position(self, pos: list[float | None]) -> None: ...
    def get_axes(self) -> list[int]: ...
