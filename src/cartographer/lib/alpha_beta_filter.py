from __future__ import annotations

import logging
from typing import final

logger = logging.getLogger(__name__)
MIN_DT = 1e-4


@final
class AlphaBetaFilter:
    def __init__(self, alpha: float = 0.5, beta: float = 1e-6):
        if not (0 <= alpha <= 1 and 0 <= beta <= 1):
            msg = "alpha and beta must be between 0 and 1"
            raise ValueError(msg)

        self.alpha = alpha
        self.beta = beta

        self.position: float | None = None  # last estimated position
        self.velocity: float = 0.0  # last estimated velocity
        self.last_time: float = 0.0  # time of last update

    def update(self, *, measurement: float, time: float) -> float:
        if self.position is None:
            self.position = measurement
            self.last_time = time
            return self.position

        dt = time - self.last_time
        self.last_time = time  # Update time even if out-of-order, to avoid stalling

        # Predict the next position
        predicted_position = self.position + self.velocity * dt

        # Calculate residual (difference from predicted to actual)
        residual = measurement - predicted_position

        # Always update position
        self.position = predicted_position + self.alpha * residual

        # Update velocity only if dt > 0
        if dt > MIN_DT:
            self.velocity = self.velocity + (self.beta * residual) / dt
        else:
            logger.debug("Skipping velocity update due to tiny or negative dt: %.6f", dt)

        return self.position
