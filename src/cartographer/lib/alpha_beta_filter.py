from __future__ import annotations

from typing import final


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
        if dt <= 0:
            msg = "timestamps must be strictly increasing"
            raise ValueError(msg)

        # Predict the next position
        predicted_position = self.position + self.velocity * dt

        # Calculate the difference between prediction and measurement
        residual = measurement - predicted_position

        # Update estimates
        self.position = predicted_position + self.alpha * residual
        self.velocity = self.velocity + (self.beta * residual) / dt
        self.last_time = time

        return self.position
