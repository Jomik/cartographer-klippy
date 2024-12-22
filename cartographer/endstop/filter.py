from __future__ import annotations
from typing import Optional, final


@final
class AlphaBetaFilter:
    estimated_position: Optional[int] = None
    estimated_velocity: float = 0.0
    previous_time: Optional[float] = None

    """
    Implements an Alpha-Beta filter for smoothing and predicting measurements.
    """

    def __init__(self, alpha: float, beta: float) -> None:
        """
        Initialize the filter with alpha and beta parameters.

        :param alpha: The smoothing factor.
        :type alpha: float
        :param beta: The prediction factor.
        :type beta: float
        """
        self.alpha = alpha  # Smoothing factor
        self.beta = beta  # Prediction factor

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
        if self.estimated_position is None:
            # First measurement initialization
            self.estimated_position = measurement

        # Compute time difference (dt)
        if self.previous_time is not None:
            delta_time = current_time - self.previous_time
        else:
            delta_time = 0.0

        # Update the time of the last measurement
        self.previous_time = current_time

        # Predict step: extrapolate position and velocity
        predicted_position = (
            self.estimated_position + self.estimated_velocity * delta_time
        )

        # Residual (difference between measurement and prediction)
        residual = measurement - predicted_position

        # Correct step: update position and velocity with alpha and beta gains
        self.estimated_position = round(predicted_position + self.alpha * residual)

        if delta_time > 0.0:
            self.estimated_velocity += (self.beta / delta_time) * residual

        return self.estimated_position
