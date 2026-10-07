from enum import StrEnum


class EntitlementStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class EntitlementSource(StrEnum):
    DIRECT = "direct"
    BUNDLE = "bundle"
