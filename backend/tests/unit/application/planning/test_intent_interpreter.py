from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.planning.intent_interpreter import IntentInterpreter


def test_interpret_extracts_location_group_size_and_budget() -> None:
    interpreter = IntentInterpreter()
    user_id = uuid4()

    result = interpreter.interpret(
        user_id,
        "I want a fun Saturday with 3 friends, R800 total, somewhere in Cape Town.",
    )

    assert result.user_id == user_id
    assert result.location == "Cape Town"
    assert result.group_size == 4
    assert result.budget_max == Decimal("800")


def test_interpret_extracts_people_as_group_size() -> None:
    interpreter = IntentInterpreter()

    result = interpreter.interpret(
        uuid4(),
        "Find something for 4 people in Cape Town.",
    )

    assert result.group_size == 4
    assert result.location == "Cape Town"


def test_interpret_returns_none_when_budget_is_missing() -> None:
    interpreter = IntentInterpreter()

    result = interpreter.interpret(
        uuid4(),
        "I want something fun in Cape Town with 3 friends.",
    )

    assert result.budget_max is None


def test_interpret_rejects_empty_request() -> None:
    interpreter = IntentInterpreter()

    with pytest.raises(ValueError, match="Planning request cannot be empty"):
        interpreter.interpret(uuid4(), "   ")
