from typing import Protocol

from reactor import ReactorTimer

class greenlet(Protocol):
    timer: ReactorTimer

def getcurrent() -> greenlet: ...
