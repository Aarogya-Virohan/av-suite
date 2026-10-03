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

    # "camera" when the photograph was taken through the in-app capture
    # screen, which applies the tripod and framing protocol and encodes
    # losslessly, "upload" when an existing file was chosen, "unknown" when
    # the client did not say. A measurement from an unguided photograph is
    # not comparable to a guided one, and without this the two are
    # indistinguishable once the file reaches the server.
    captureSource: str
