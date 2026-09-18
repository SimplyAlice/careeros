from uuid import uuid4

import pytest

from app.domain.entities.audit_log import AuditAction, AuditLog


def test_audit_log_can_be_created():
    log = AuditLog(
        id=uuid4(),
        action_id=uuid4(),
        action=AuditAction.ACTION_REQUESTED,
        message="Restart service action requested.",
    )

    assert log.action == AuditAction.ACTION_REQUESTED
    assert log.message == "Restart service action requested."


def test_audit_log_requires_action_id():
    action_id = uuid4()

    log = AuditLog(
        id=uuid4(),
        action_id=action_id,
        action=AuditAction.ACTION_APPROVED,
        message="Action approved by operator.",
    )

    assert log.action_id == action_id


def test_audit_log_rejects_empty_message():
    with pytest.raises(ValueError, match="Audit log message cannot be empty"):
        AuditLog(
            id=uuid4(),
            action_id=uuid4(),
            action=AuditAction.ACTION_FAILED,
            message="",
        )


def test_audit_log_rejects_whitespace_message():
    with pytest.raises(ValueError, match="Audit log message cannot be empty"):
        AuditLog(
            id=uuid4(),
            action_id=uuid4(),
            action=AuditAction.ACTION_EXECUTED,
            message="   ",
        )