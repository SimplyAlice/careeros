"""add generated resumes and cover letters

Revision ID: 99437a80b3b3
Revises: 980eb04284d4
Create Date: 2026-07-26 20:53:09.196618

Milestone 6: two new, independent tables for AI-generated, versioned,
PDF-rendered documents. Deliberately new tables rather than reusing
`resumes` (Milestone 2, unused, tied to `users`) or `resume_metadata`
(Milestone 4, upload metadata only) — see
`docs/adr/0014-resume-cover-letter-generation.md`. No existing table is
altered by this migration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "99437a80b3b3"
down_revision: str | None = "980eb04284d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_cover_letters",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_generated_cover_letters_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_generated_cover_letters_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generated_cover_letters")),
    )
    op.create_index(
        op.f("ix_generated_cover_letters_job_id"), "generated_cover_letters", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_generated_cover_letters_profile_id"), "generated_cover_letters", ["profile_id"], unique=False
    )
    op.create_table(
        "generated_resumes",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("professional_summary", sa.Text(), nullable=False),
        sa.Column(
            "emphasized_skills", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_generated_resumes_job_id_jobs"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiles.id"], name=op.f("fk_generated_resumes_profile_id_profiles"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generated_resumes")),
    )
    op.create_index(op.f("ix_generated_resumes_job_id"), "generated_resumes", ["job_id"], unique=False)
    op.create_index(op.f("ix_generated_resumes_profile_id"), "generated_resumes", ["profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_resumes_profile_id"), table_name="generated_resumes")
    op.drop_index(op.f("ix_generated_resumes_job_id"), table_name="generated_resumes")
    op.drop_table("generated_resumes")
    op.drop_index(op.f("ix_generated_cover_letters_profile_id"), table_name="generated_cover_letters")
    op.drop_index(op.f("ix_generated_cover_letters_job_id"), table_name="generated_cover_letters")
    op.drop_table("generated_cover_letters")
