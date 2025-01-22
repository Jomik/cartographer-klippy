from __future__ import annotations

from typing import final

_ALPHA = 0.5
_BETA = 1e-6


@final
class AlphaBetaFilter:
    _estimated_position: int | None = None
    _estimated_velocity: float = 0.0
    _previous_time: float | None = None

    """
    Implements an Alpha-Beta filter for smoothing and predicting measurements.
    """

    def __init__(self, alpha: float = _ALPHA, beta: float = _BETA) -> None:
        """
        Initialize the filter with alpha and beta parameters.

        :param alpha: The smoothing factor.
        :type alpha: float
        :param beta: The prediction factor.
        :type beta: float
        """
        self._alpha = alpha  # Smoothing factor
        self._beta = beta  # Prediction factor

    def update(self, current_time: float, measurement: int) -> int:
        """
        Update the filter with a new measurement.

        :param current_time: The current time.
        :type current_time: float
        :param measurement: The new measurement (integer count).
        :type measurement: int
        :return: The updated estimated position (integer).
        :rtype: int
        """
        if self._estimated_position is None:
            # First measurement initialization
            self._estimated_position = measurement

        # Compute time difference (dt)
        if self._previous_time is not None:
            delta_time = current_time - self._previous_time
        else:
            delta_time = 0.0

        # Update the time of the last measurement
        self._previous_time = current_time

        # Predict step: extrapolate position and velocity
        predicted_position = (
            self._estimated_position + self._estimated_velocity * delta_time
        )

        # Residual (difference between measurement and prediction)
        residual = measurement - predicted_position

        # Correct step: update position and velocity with alpha and beta gains
        self._estimated_position = round(predicted_position + self._alpha * residual)

        if delta_time > 0.0:
            self._estimated_velocity += (self._beta / delta_time) * residual

        return self._estimated_position
