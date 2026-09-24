"""add plan item status

Revision ID: 4d8f1e2a3c5b
Revises: 2c2b1736f4ad
Create Date: 2026-09-24 03:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "4d8f1e2a3c5b"
down_revision: str | None = "2c2b1736f4ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plan_items",
        sa.Column("status", sa.String(50), nullable=False, server_default="planned"),
    )


def downgrade() -> None:
    op.drop_column("plan_items", "status")
