from typing import Dict, List
from app.enums.user import UserRole

# Centralized Permission Map
# Maps a resource/feature area to the list of roles that are allowed to access it.
# Adding a new role (e.g., Manager) is as simple as adding it to the appropriate lists here.
PERMISSION_MAP: Dict[str, List[UserRole]] = {
    "patients": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "treatments": [UserRole.ADMIN, UserRole.THERAPIST],
    "assessments": [UserRole.ADMIN, UserRole.THERAPIST],
    "billing": [UserRole.ADMIN, UserRole.FRONT_DESK],
    "analytics": [UserRole.ADMIN, UserRole.THERAPIST],  # RBAC Spec §4: Front Desk has NO analytics access
    "leads": [UserRole.ADMIN, UserRole.FRONT_DESK],
    "documents": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "appointments": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "exercises": [UserRole.ADMIN, UserRole.THERAPIST],
    "posture": [UserRole.ADMIN, UserRole.THERAPIST],
    "prescriptions": [UserRole.ADMIN, UserRole.THERAPIST],
    "settings": [UserRole.ADMIN],
    "packages": [UserRole.ADMIN],
    "clinic_admin": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "booking": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "appointment_requests": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
}
