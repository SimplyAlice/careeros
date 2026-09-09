from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Incident:
    id: UUID
    service_id: UUID
    title: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Incident title cannot be empty.")