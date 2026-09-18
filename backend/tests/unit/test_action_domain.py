from uuid import uuid4

import pytest

from app.domain.entities.action import (
    Action,
    ActionStatus,
    ActionType,
)


def test_action_can_be_created():
    action = Action(
        id=uuid4(),
        service_id=uuid4(),
        action_type=ActionType.RESTART_SERVICE,
        reason="Service is unresponsive.",
    )

    assert action.action_type == ActionType.RESTART_SERVICE
    assert action.reason == "Service is unresponsive."
    assert action.status == ActionStatus.PENDING


def test_action_can_have_different_status():
    action = Action(
        id=uuid4(),
        service_id=uuid4(),
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        reason="Latest deployment introduced errors.",
        status=ActionStatus.APPROVED,
    )

    assert action.status == ActionStatus.APPROVED


def test_action_requires_service_id():
    service_id = uuid4()

    action = Action(
        id=uuid4(),
        service_id=service_id,
        action_type=ActionType.SCALE_SERVICE,
        reason="Traffic has increased significantly.",
    )

    assert action.service_id == service_id


def test_action_rejects_empty_reason():
    with pytest.raises(ValueError, match="Action reason cannot be empty"):
        Action(
            id=uuid4(),
            service_id=uuid4(),
            action_type=ActionType.RESTART_SERVICE,
            reason="",
        )


def test_action_rejects_whitespace_reason():
    with pytest.raises(ValueError, match="Action reason cannot be empty"):
        Action(
            id=uuid4(),
            service_id=uuid4(),
            action_type=ActionType.ACKNOWLEDGE_INCIDENT,
            reason="   ",
        )