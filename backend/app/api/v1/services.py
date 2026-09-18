from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_service_service
from app.application.services.service_service import ServiceService
from app.domain.entities.service import ServiceStatus

router = APIRouter(prefix="/services", tags=["services"])


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    environment: str
    status: ServiceStatus


class ServiceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    environment: str = Field(..., min_length=1, max_length=100)
    status: ServiceStatus = ServiceStatus.UNKNOWN


@router.get("", response_model=list[ServiceRead], summary="List operational services")
async def list_services(
    service: Annotated[ServiceService, Depends(get_service_service)],
) -> list[ServiceRead]:
    services = await service.list_services()
    return [ServiceRead.model_validate(item) for item in services]


@router.get("/{service_id}", response_model=ServiceRead, summary="Get an operational service")
async def get_service(
    service_id: UUID,
    service: Annotated[ServiceService, Depends(get_service_service)],
) -> ServiceRead:
    item = await service.get_service(service_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")
    return ServiceRead.model_validate(item)


@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an operational service",
)
async def create_service(
    body: ServiceCreateRequest,
    service: Annotated[ServiceService, Depends(get_service_service)],
) -> ServiceRead:
    item = await service.create_service(
        name=body.name,
        environment=body.environment,
        status=body.status,
    )
    return ServiceRead.model_validate(item)
