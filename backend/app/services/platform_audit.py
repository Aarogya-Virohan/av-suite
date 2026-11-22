from app.models.platform import PlatformAuditLog


def record_platform_audit(session, *, operator_id=None, action, target_type, target_id=None,
                          reason=None, ip=None, user_agent=None, details=None,
                          organization_id=None, clinic_id=None):
    """Add a sanitized platform audit record to the caller's transaction."""
    session.add(PlatformAuditLog(
        operator_id=operator_id, action=action, target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        reason=reason, ip=ip, user_agent=user_agent,
        details=details or {}, organization_id=organization_id, clinic_id=clinic_id,
    ))
