"""add plan item position

Revision ID: 2c2b1736f4ad
Revises: 3633f5cc813a
Create Date: 2026-09-21 23:30:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2c2b1736f4ad"
down_revision: str | None = "3633f5cc813a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plan_items",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("plan_items", "position")
