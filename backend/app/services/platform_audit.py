import logging

from app.core.database import AsyncSessionLocal
from app.models.platform import PlatformAuditLog

logger = logging.getLogger(__name__)


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


async def record_platform_audit_isolated(**kwargs) -> None:
    """Write one platform audit row in its own session and commit it.

    For events on a request that ends in an error (failed login): the request
    session is rolled back then, so a row added there would be lost. Never
    raises; auditing must not change the answer to the caller.

    Do not pass operator_id here: this runs in a second connection while the
    request may hold a row lock on the operator (MFA uses FOR UPDATE), and the
    foreign key check on operator_id would wait for that lock forever. A failed
    attempt has no authenticated actor anyway; the operator goes in target_id.
    """
    try:
        async with AsyncSessionLocal() as session:
            record_platform_audit(session, **kwargs)
            await session.commit()
    except Exception as exc:
        logger.warning("Could not write platform audit row (%s): %s", kwargs.get("action"), exc)
