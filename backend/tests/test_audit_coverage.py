import ast
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.audit import log_event_safely


BACKEND = Path(__file__).parents[1]


class AuditSession:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        pass

    async def refresh(self, value):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass


@pytest.mark.asyncio
async def test_audit_helper_persists_safe_event_fields():
    session = AuditSession()
    clinic_id, user_id, entity_id = uuid4(), uuid4(), uuid4()

    await log_event_safely(
        session, clinic_id, user_id, "create", "lead", entity_id,
        {"stage": "new"},
    )

    [event] = session.added
    assert event.clinic_id == clinic_id
    assert event.user_id == user_id
    assert event.action == "create"
    assert event.entity_type == "lead"
    assert event.entity_id == entity_id
    assert event.details == {"stage": "new"}
    assert not {"password", "password_hash", "token", "secret", "authorization"} & set(event.details)


@pytest.mark.parametrize(
    ("filename", "handler", "action", "entity"),
    [
        ("leads.py", "create_lead", "create", "lead"),
        ("leads.py", "update_lead", "update", "lead"),
        ("leads.py", "convert_lead", "convert", "lead"),
        ("leads.py", "delete_lead", "delete", "lead"),
        ("appointments.py", "create_appointment", "create", "appointment"),
        ("appointments.py", "update_appointment", "update", "appointment"),
        ("appointments.py", "soft_cancel_appointment", "cancel", "appointment"),
        ("billing.py", "create_invoice", "create", "invoice"),
        ("billing.py", "update_invoice", "update", "invoice"),
        ("billing.py", "delete_invoice", "delete", "invoice"),
        ("billing.py", "record_payment", "create", "payment"),
        ("billing.py", "record_payment_for_invoice", "create", "payment"),
        ("billing.py", "void_payment", "void", "payment"),
        ("users.py", "create_user", "create", "user"),
        # BE fixes (report D3): the clinical record, Rx, documents and fee list.
        ("prescriptions.py", "create_prescription", "create", "prescription"),
        ("prescriptions.py", "update_prescription", "update", "prescription"),
        ("prescriptions.py", "delete_prescription", "delete", "prescription"),
        ("prescriptions.py", "generate_pdf", "generate_pdf", "prescription"),
        ("documents.py", "upload_patient_document", "upload", "document"),
        ("documents.py", "create_document", "upload", "document"),
        ("documents.py", "delete_document", "delete", "document"),
        ("assessments.py", "create_soap_assessment", "create", "soap_assessment"),
        ("assessments.py", "update_soap_assessment", "update", "soap_assessment"),
        ("treatments.py", "create_treatment_session", "create", "treatment_session"),
        ("treatments.py", "update_treatment_session", "update", "treatment_session"),
        ("treatments.py", "delete_treatment_session", "delete", "treatment_session"),
        ("settings.py", "create_fee_item", "create", "fee_item"),
        ("settings.py", "update_fee_item", "update", "fee_item"),
        ("settings.py", "deactivate_fee_item", "delete", "fee_item"),
    ],
)
def test_required_handlers_emit_audit_event(filename, handler, action, entity):
    module = ast.parse((BACKEND / "app" / "api" / "v1" / filename).read_text())
    function = next(node for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == handler)
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "log_event_safely"]
    assert any(
        len(call.args) >= 5
        and isinstance(call.args[3], ast.Constant) and call.args[3].value == action
        and isinstance(call.args[4], ast.Constant) and call.args[4].value == entity
        for call in calls
    )


def test_lead_stage_transition_audit_has_old_and_new_values():
    module = ast.parse((BACKEND / "app" / "api" / "v1" / "leads.py").read_text())
    function = next(node for node in module.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "update_lead")
    source = ast.unparse(function)
    assert "old_stage" in source and "new_stage" in source
    assert "if old_stage != lead.stage" in source
