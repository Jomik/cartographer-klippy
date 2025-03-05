# https://github.com/Klipper3d/klipper/blob/master/klippy/reactor.py

from typing import Any, Callable, overload

class ReactorTimer: ...

_NOW: float
_NEVER: float

class ReactorCompletion[T = Any]:
    def test(self) -> bool: ...
    def complete(self, result: T) -> None: ...
    @overload
    def wait(self, waketime: float, waketime_result: T) -> T: ...
    @overload
    def wait(self) -> T | None: ...

class Reactor:
    NOW: float
    NEVER: float
    monotonic: Callable[[], float]
    def register_timer(self, callback: Callable[[float], float], waketime: float = ...) -> ReactorTimer: ...
    def update_timer(self, timer_handler: ReactorTimer, waketime: float) -> None: ...
    def register_async_callback(self, callback: Callable[[float], None], waketime: float = ...) -> None: ...
    def pause(self, waketime: float) -> float: ...
    def completion(self) -> ReactorCompletion: ...
