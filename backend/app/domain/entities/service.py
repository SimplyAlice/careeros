from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class Service:
    id: UUID
    name: str
    environment: str
    status: ServiceStatus = ServiceStatus.UNKNOWN

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Service name cannot be empty.")

        if not self.environment.strip():
            raise ValueError("Service environment cannot be empty.")
