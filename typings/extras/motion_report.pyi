from typing import Tuple

class DumpTrapQ:
    def get_trapq_position(
        self, print_time: float
    ) -> Tuple[None, None] | Tuple[list[float], float]: ...

class PrinterMotionReport:
    trapqs: dict[str, DumpTrapQ]
