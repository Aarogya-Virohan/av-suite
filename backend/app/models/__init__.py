from app.models.base import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin
from app.models.clinic import Clinic, ClinicPlanTier
from app.models.user import User
from app.models.membership import Membership
from app.models.user_permission import UserPermission
from app.models.product import (
    PlatformBundle,
    PlatformBundleProduct,
    Product,
    WorkspaceProduct,
)
from app.models.patient import Patient, PatientStatus
from app.models.exercise import Exercise
from app.models.exercise_photo import ExercisePhoto
from app.models.exercise_category import ExerciseCategory, exercise_category_links
from app.models.prescription import Prescription, PrescriptionItem
from app.models.exercise_template import ExerciseTemplate, ExerciseTemplateItem
from app.models.posture_session import PostureSession, PostureMeasurement

# --- CRM models ---
from app.models.lead import Lead
from app.models.appointment import Appointment
from app.models.booking import AppointmentRequest
from app.models.treatment import TreatmentSession, SoapAssessment
from app.models.billing import Package, PatientPackage, Invoice, InvoiceItem, Payment
from app.models.document import PatientDocument
from app.models.audit import AuditLog
from app.models.psychosocial import (
    PsychosocialAssignment,
    PsychosocialClinicSetting,
    PsychosocialConsent,
    PsychosocialConsentRequest,
    PsychosocialReferralAction,
    PsychosocialReferralContact,
    PsychosocialSchedule,
    PsychosocialSession,
    PsychosocialSessionReview,
    PsychosocialSharedReport,
)
from app.models.clinic_fee_item import ClinicFeeItem

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
    "Clinic",
    "ClinicPlanTier",
    "User",
    "Membership",
    "UserPermission",
    "Product",
    "PlatformBundle",
    "PlatformBundleProduct",
    "WorkspaceProduct",
    "Patient",
    "PatientStatus",
    "Exercise",
    "ExercisePhoto",
    "ExerciseCategory",
    "exercise_category_links",
    "Prescription",
    "PrescriptionItem",
    "ExerciseTemplate",
    "ExerciseTemplateItem",
    "PostureSession",
    "PostureMeasurement",
    "Lead",
    "Appointment",
    "AppointmentRequest",
    "TreatmentSession",
    "SoapAssessment",
    "Package",
    "PatientPackage",
    "Invoice",
    "InvoiceItem",
    "Payment",
    "PatientDocument",
    "AuditLog",
    "PsychosocialAssignment",
    "PsychosocialSession",
    "PsychosocialConsent",
    "PsychosocialReferralAction",
    "PsychosocialSchedule",
    "PsychosocialClinicSetting",
    "PsychosocialReferralContact",
    "PsychosocialSessionReview",
    "PsychosocialConsentRequest",
    "PsychosocialSharedReport",
    "ClinicFeeItem",
]
