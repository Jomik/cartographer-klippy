from enum import Enum
from typing import Protocol


class ConfigWrapper(Protocol): ...


class Environment(Enum):
    Klipper = "klipper"
    Kalico = "kalico"


def detect_environment() -> Environment:
    return Environment.Klipper
