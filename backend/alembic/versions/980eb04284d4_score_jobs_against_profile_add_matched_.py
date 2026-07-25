"""score jobs against profile, add matched/missing skills

Revision ID: 980eb04284d4
Revises: a9b65b32aeda
Create Date: 2026-07-24 18:04:19.872090

Milestone 5's scoring engine needs to attach a `JobMatch` to the actual
single local profile Milestone 4 introduced — `job_matches.user_id`
(Milestone 2) can't be populated yet since there's no registration flow
to create real `users` rows. See
`docs/adr/0013-score-against-profile-not-user.md` for the full reasoning.

- Adds `profile_id` (FK to `profiles.id`, nullable — no backfill exists
  for any pre-existing rows, mirroring how `docs/adr/0012-profile-management.md`
  handled the equivalent situation for `candidate_profiles`).
- Makes `user_id` nullable (kept, not dropped, ready to become the real
  per-user reference once auth lands).
- Adds `matched_skills`/`missing_skills` (JSONB string arrays) so the
  scoring engine's structured output doesn't have to be folded into the
  existing `reasoning` text column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "980eb04284d4"
down_revision: str | None = "a9b65b32aeda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("job_matches", sa.Column("profile_id", sa.UUID(), nullable=True))
    op.add_column(
        "job_matches",
        sa.Column("matched_skills", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
    )
    op.add_column(
        "job_matches",
        sa.Column("missing_skills", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
    )
    op.alter_column("job_matches", "user_id", existing_type=sa.UUID(), nullable=True)
    op.create_index(op.f("ix_job_matches_profile_id"), "job_matches", ["profile_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_job_matches_profile_id_profiles"),
        "job_matches",
        "profiles",
        ["profile_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_job_matches_profile_id_profiles"), "job_matches", type_="foreignkey")
    op.drop_index(op.f("ix_job_matches_profile_id"), table_name="job_matches")
    op.alter_column("job_matches", "user_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("job_matches", "missing_skills")
    op.drop_column("job_matches", "matched_skills")
    op.drop_column("job_matches", "profile_id")
