from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Context:
    error: Exception | None = None
