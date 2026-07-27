"""Application-level errors for resume/cover-letter generation use cases."""

from __future__ import annotations


class DocumentGenerationResponseError(Exception):
    """Raised when the LLM provider's response can't be parsed into valid
    generated content — mirrors `ScoringResponseError`
    (`app/application/scoring/scoring_service.py`, Milestone 5): a bad/
    garbled upstream response, not a business validation failure. The API
    layer maps this to a 502.
    """
