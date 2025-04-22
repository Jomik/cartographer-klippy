from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from klippy import Printer
    from webhooks import WebRequest

    from cartographer.klipper.mcu.mcu import KlipperCartographerMcu, Sample
    from cartographer.printer_interface import Position, Toolhead
    from cartographer.probe.scan_mode import ScanMode

logger = logging.getLogger(__name__)


BUFFER_SIZE = 50


@dataclass
class WebhookSample:
    time: float
    frequency: float
    temperature: float
    position: Position | None
    distance: float | None


@final
class KlipperCartographerWebhooks:
    def __init__(
        self,
        printer: Printer,
        mcu: KlipperCartographerMcu,
        toolhead: Toolhead,
        scan_mode: ScanMode[object, Sample],
    ) -> None:
        self._printer = printer
        self._mcu = mcu
        self._toolhead = toolhead
        self.scan_mode = scan_mode

    def register(self) -> None:
        """Register the webhooks with Klipper."""
        webhooks = self._printer.lookup_object("webhooks")
        webhooks.register_endpoint("cartographer/subscribe_samples", self._handle_subscribe_samples)

    def _handle_subscribe_samples(self, web_request: WebRequest) -> None:
        conn = web_request.get_client_connection()
        logger.debug("Sample subscription received %d", id(conn))
        template = web_request.get_dict("response_template", default={})

        # PERF: Share buffer
        buffer: list[WebhookSample] = []

        session = self._mcu.start_session()

        def callback(sample: Sample):
            session.items.clear()
            if conn.is_closed():
                logger.debug("Connection %d closed, stopping subscription", id(conn))
                with session:
                    return "done"

            position = self._toolhead.get_requested_position(sample.time)
            distance = self._frequency_to_distance(sample.frequency)
            buffer.append(
                WebhookSample(
                    time=sample.time,
                    frequency=sample.frequency,
                    temperature=sample.temperature,
                    position=position,
                    distance=distance,
                )
            )
            if len(buffer) >= BUFFER_SIZE:
                response = dict(template)
                response["params"] = {"samples": list(map(asdict, buffer))}
                buffer.clear()
                conn.send(response)

        self._mcu.register_callback(callback)

    def _frequency_to_distance(self, frequency: float) -> float | None:
        if self.scan_mode.model is None:
            return None
        dist = self.scan_mode.model.frequency_to_distance(frequency)
        if math.isinf(dist):
            return None
        return dist
