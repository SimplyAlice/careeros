from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Plan:
    intention: str
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    status: str = "draft"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.intention.strip():
            raise ValueError("Plan intention cannot be empty.")

        if self.title is not None and not self.title.strip():
            raise ValueError("Plan title cannot be empty.")

    def update_title(self, title: str) -> None:
        if not title.strip():
            raise ValueError("Plan title cannot be empty.")

        self.title = title.strip()
        self.updated_at = datetime.now(UTC)
