from datetime import UTC, datetime
from uuid import uuid4
import pytest

from app.domain.entities.planning.information import FreshnessKind
from app.domain.entities.planning.live_intelligence import (
    LiveChangeType,
    LiveSignal,
    LiveSignalType,
    PlanHealthCheckResult,
    PlanHealthStatus,
)


def test_live_signal_creation_and_validation() -> None:
    now = datetime.now(UTC)
    item_id = uuid4()
    signal = LiveSignal(
        source="open-meteo",
        signal_type=LiveSignalType.WEATHER,
        observed_at=now,
        freshness=FreshnessKind.LIVE,
        target_name="Kirstenbosch",
        target_item_id=item_id,
        change_type=LiveChangeType.WEATHER_UNSUITABLE,
        current_value={"condition": "Rain"},
        is_meaningful_change=True,
        message="Rain forecast during outdoor activity.",
    )
    assert signal.source == "open-meteo"
    assert signal.target_name == "Kirstenbosch"
    assert signal.is_meaningful_change is True
    assert signal.change_type is LiveChangeType.WEATHER_UNSUITABLE

    with pytest.raises(ValueError, match="Live signal source cannot be empty"):
        LiveSignal(
            source="",
            signal_type=LiveSignalType.WEATHER,
            observed_at=now,
            freshness=FreshnessKind.LIVE,
            target_name="Kirstenbosch",
        )

    with pytest.raises(ValueError, match="Live signal target name cannot be empty"):
        LiveSignal(
            source="open-meteo",
            signal_type=LiveSignalType.WEATHER,
            observed_at=now,
            freshness=FreshnessKind.LIVE,
            target_name="   ",
        )


def test_plan_health_check_result_creation_and_validation() -> None:
    plan_id = uuid4()
    now = datetime.now(UTC)
    result = PlanHealthCheckResult(
        plan_id=plan_id,
        health_status=PlanHealthStatus.HEALTHY,
        headline="Your plan still looks good",
        narrative="All venues verified open and weather conditions are suitable.",
        signals=[],
        checked_at=now,
    )
    assert result.plan_id == plan_id
    assert result.health_status is PlanHealthStatus.HEALTHY
    assert result.proposed_adaptation is None

    with pytest.raises(ValueError, match="Health check headline cannot be empty"):
        PlanHealthCheckResult(
            plan_id=plan_id,
            health_status=PlanHealthStatus.HEALTHY,
            headline="",
            narrative="Some narrative",
            signals=[],
            checked_at=now,
        )

    with pytest.raises(ValueError, match="Health check narrative cannot be empty"):
        PlanHealthCheckResult(
            plan_id=plan_id,
            health_status=PlanHealthStatus.HEALTHY,
            headline="Headline",
            narrative="   ",
            signals=[],
            checked_at=now,
        )
