from uuid import uuid4

import pytest

from app.domain.entities.approval import Approval, ApprovalStatus


def test_approval_defaults_to_pending():
    approval = Approval(
        id=uuid4(),
        action_id=uuid4(),
    )

    assert approval.status == ApprovalStatus.PENDING


def test_pending_approval_can_be_approved():
    approval = Approval(
        id=uuid4(),
        action_id=uuid4(),
    )

    approval.approve()

    assert approval.status == ApprovalStatus.APPROVED


def test_pending_approval_can_be_rejected():
    approval = Approval(
        id=uuid4(),
        action_id=uuid4(),
    )

    approval.reject()

    assert approval.status == ApprovalStatus.REJECTED


def test_approved_approval_cannot_be_approved_again():
    approval = Approval(
        id=uuid4(),
        action_id=uuid4(),
    )

    approval.approve()

    with pytest.raises(
        ValueError,
        match="Only pending approvals can be approved",
    ):
        approval.approve()


def test_rejected_approval_cannot_be_rejected_again():
    approval = Approval(
        id=uuid4(),
        action_id=uuid4(),
    )

    approval.reject()

    with pytest.raises(
        ValueError,
        match="Only pending approvals can be rejected",
    ):
        approval.reject()
        