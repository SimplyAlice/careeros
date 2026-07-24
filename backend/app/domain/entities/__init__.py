"""Domain entities.

- `profile.py` — `Profile`, `Skill`, `Experience`, `Education`,
  `ResumeMetadata` — added in Milestone 4.

`Job`, `Application`, and the other Milestone 2/3 entities are
intentionally represented directly by their SQLAlchemy models
(`app/infrastructure/db/models/`) rather than duplicated here — that
pragmatic choice is unchanged by this package gaining its first real
occupant. See `app/domain/entities/profile.py`'s module docstring for why
`Profile` gets a distinct domain entity where `Job` didn't.
"""
