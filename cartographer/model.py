from __future__ import annotations

from typing import final

from configfile import ConfigWrapper
from numpy.polynomial import Polynomial


@final
class ScannerModel:
    @staticmethod
    def load(config: ConfigWrapper):
        name = config.get_name()
        temp = config.getfloat("temperature")
        coef = config.getfloatlist("coefficient")
        domain = config.getfloatlist("domain", count=2)
        [min_z, max_z] = config.getfloatlist("z_range", count=2)
        checksum = config.get("checksum")
        poly = Polynomial(coef, domain)
        return ScannerModel(name, poly, temp, min_z, max_z, checksum)

    def __init__(
        self,
        name: str,
        poly: Polynomial,
        temp: float,
        min_z: float,
        max_z: float,
        checksum: str,
    ):
        self.name = name
        self.poly = poly
        self.min_z = min_z
        self.max_z = max_z
        self.temp = temp
        self.checksum = checksum
