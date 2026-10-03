from dataclasses import dataclass
from typing import Literal

Severity = Literal["none", "mild", "moderate", "severe", "insufficient_data"]


@dataclass
class Landmark:
    index: int
    x: float
    y: float
    z: float
    visibility: float


@dataclass
class Measurement:
    label: str
    value: float | str
    unit: str
    severityLabel: str
    severity: Severity


@dataclass
class ViewResult:
    photoUrl: str
    accuracy: float
    measurements: list[Measurement]
    interpretation: str
