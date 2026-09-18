from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class EventType(str, Enum):
    ERROR = "error"
    DEPLOYMENT = "deployment"
    HEALTH_CHECK = "health_check"
    ALERT = "alert"
    SYSTEM = "system"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Event:
    id: UUID
    service_id: UUID
    event_type: EventType
    severity: EventSeverity
    message: str
    incident_id: UUID | None = None
    evaluation_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Event message cannot be empty.")
