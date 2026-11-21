from enum import StrEnum


class OrganizationType(StrEnum):
    INDIVIDUAL = "individual"
    CLINIC = "clinic"
    CHAIN = "chain"
    FRANCHISE = "franchise"
    HOSPITAL = "hospital"
    GOVERNMENT = "government"
    PARTNER_PLATFORM = "partner_platform"


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class OrganizationRole(StrEnum):
    ORG_OWNER = "org_owner"
    ORG_ADMIN = "org_admin"
    ORG_VIEWER = "org_viewer"


class ClinicStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
