from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cartographer.printer import HomingState


class EndstopMode(ABC):
    """Abstract base class for endstop modes."""

    def on_enter(self) -> None:
        """Called when switching into this mode."""
        return

    def on_exit(self) -> None:
        """Called when switching out of this mode."""
        return

    def can_switch(self) -> bool:
        """Determine if switching to a new mode is allowed."""
        return True

    @abstractmethod
    def query_is_triggered(self, print_time: float) -> bool:
        """Return true if endstop is currently triggered"""

    @abstractmethod
    def get_endstop_position(self) -> float:
        """Returns the position at which the endstop is triggered"""

    @abstractmethod
    def home_start(self, print_time: float) -> object:
        """Start the homing process"""

    @abstractmethod
    def on_home_end(self, homing_state: HomingState) -> None:
        """Called when homing moves are done."""
