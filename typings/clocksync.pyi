# https://github.com/Klipper3d/klipper/blob/master/klippy/clocksync.py

class ClockSync:
    def print_time_to_clock(self, print_time: float) -> int: ...
    def clock_to_print_time(self, clock: int) -> float: ...
    def clock32_to_clock64(self, clock32: int) -> int: ...
