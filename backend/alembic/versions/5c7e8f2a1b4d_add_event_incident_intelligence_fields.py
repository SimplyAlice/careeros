"""add Event to Incident intelligence fields

Revision ID: 5c7e8f2a1b4d
Revises: 344c416f9866
Create Date: 2026-09-18 00:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c7e8f2a1b4d"
down_revision: str | None = "344c416f9866"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("incident_id", sa.Uuid(), nullable=True))
    op.add_column("events", sa.Column("evaluation_reason", sa.String(length=1000), nullable=True))
    op.create_foreign_key(
        "fk_events_incident_id_incidents",
        "events",
        "incidents",
        ["incident_id"],
        ["id"],
    )
    op.add_column("incidents", sa.Column("detection_reason", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "detection_reason")
    op.drop_constraint("fk_events_incident_id_incidents", "events", type_="foreignkey")
    op.drop_column("events", "evaluation_reason")
    op.drop_column("events", "incident_id")
