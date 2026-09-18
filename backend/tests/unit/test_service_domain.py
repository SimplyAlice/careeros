from uuid import uuid4

import pytest

from app.domain.entities.service import Service, ServiceStatus


def test_service_can_be_created():
    service = Service(
        id=uuid4(),
        name="payments-api",
        environment="production",
        status=ServiceStatus.HEALTHY,
    )

    assert service.name == "payments-api"
    assert service.environment == "production"
    assert service.status == ServiceStatus.HEALTHY


def test_service_defaults_to_unknown_status():
    service = Service(
        id=uuid4(),
        name="payments-api",
        environment="production",
    )

    assert service.status == ServiceStatus.UNKNOWN


def test_service_rejects_empty_name():
    with pytest.raises(ValueError, match="Service name cannot be empty"):
        Service(
            id=uuid4(),
            name="",
            environment="production",
        )


def test_service_rejects_empty_environment():
    with pytest.raises(ValueError, match="Service environment cannot be empty"):
        Service(
            id=uuid4(),
            name="payments-api",
            environment="",
        )