from dataclasses import dataclass
from typing import Literal

Severity = Literal["none", "mild", "moderate", "severe", "insufficient_data", "not_available"]


@dataclass
class Landmark:
    index: int
    x: float
    y: float
    z: float
    visibility: float


@dataclass
class Measurement:
    # Nothing constructs this; report_builder.measurement() returns a plain
    # dict and no route validates against it. It documents the payload shape,
    # so it had drifted behind the three fields below. Kept and corrected
    # rather than deleted, in case it is being read as the API contract.
    paramId: str
    label: str
    value: float | str
    unit: str
    severityLabel: str
    severity: Severity
    borderline: bool
    side: str | None
    sideLabel: str | None


@dataclass
class ViewResult:
    photoUrl: str
    accuracy: float
    measurements: list[Measurement]
    interpretation: str
