class DumpTrapQ:
    def get_trapq_position(self, print_time: float) -> tuple[None, None] | tuple[list[float], float]: ...

class PrinterMotionReport:
    trapqs: dict[str, DumpTrapQ]
