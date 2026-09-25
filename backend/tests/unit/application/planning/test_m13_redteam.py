"""Red-team test script for M13 to evaluate existing engine against difficult natural-language scenarios."""
import asyncio
from decimal import Decimal
from uuid import uuid4
import pytest

from app.application.planning.understanding_service import DeterministicUnderstandingEngine
from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.information import PlanningInformationService
from app.domain.entities.planning.decision import DecisionCriteria
from app.domain.entities.planning.decision_engine import decide
from app.infrastructure.planning.fixture_provider import CapeTownFixtureInformationProvider
FIXTURE_PLACES = CapeTownFixtureInformationProvider._places
FIXTURE_ACTIVITIES = CapeTownFixtureInformationProvider._activities


@pytest.fixture
def engine():
    return DeterministicUnderstandingEngine()


def test_redteam_budget_scenarios(engine):
    # 1. "I have R300 for two people for the whole afternoon."
    u1 = engine.parse("I have R300 for two people for the whole afternoon.")
    print("\n--- R300 for two people ---")
    print(f"People: {u1.people_count}, Budget: {u1.budget_amount} ({u1.budget_kind}), Duration: {u1.duration_limit_minutes}, Window: {u1.time_window}")

    # 2. "Under R500 but I don't mind spending most of it on dinner."
    u2 = engine.parse("Under R500 but I don't mind spending most of it on dinner.")
    print("\n--- Under R500, spend most on dinner ---")
    print(f"Budget: {u2.budget_amount} ({u2.budget_kind}), Preferences: {u2.preferences}, Descriptors: {u2.semantic_descriptors}")

    # 3. "Cheap date but somewhere that doesn't feel cheap."
    u3 = engine.parse("Cheap date but somewhere that doesn't feel cheap.")
    print("\n--- Cheap date but doesn't feel cheap ---")
    print(f"Budget: {u3.budget_amount} ({u3.budget_kind}), Occasion: {u3.occasion}, Exclusions: {u3.exclusions}, Preferences: {u3.preferences}")


def test_redteam_time_scenarios(engine):
    # 4. "I have two hours before I need to be home."
    u4 = engine.parse("I have two hours before I need to be home.")
    print("\n--- Two hours before I need to be home ---")
    print(f"Duration: {u4.duration_limit_minutes}, End time: {u4.end_time}, Ambiguities: {u4.ambiguities}")

    # 5. "Dinner after 7 but I need to leave by 9."
    u5 = engine.parse("Dinner after 7 but I need to leave by 9.")
    print("\n--- Dinner after 7 but leave by 9 ---")
    print(f"Start: {u5.start_time}, End: {u5.end_time}, Window: {u5.time_window}")

    # 6. "We're free Saturday afternoon."
    u6 = engine.parse("We're free Saturday afternoon.")
    print("\n--- Free Saturday afternoon ---")
    print(f"Date: {u6.date_spec}, Window: {u6.time_window}, Budget: {u6.budget_amount} ({u6.budget_kind})")


def test_redteam_weather_and_multi_constraints(engine):
    # 7. "It's raining and we don't want to be outside."
    u7 = engine.parse("It's raining and we don't want to be outside.")
    print("\n--- Raining and don't want to be outside ---")
    print(f"Weather: {u7.weather_context}, Setting: {u7.setting_preference}, Exclusions: {u7.exclusions}")

    # 8. "It's sunny, let's do something outdoors."
    u8 = engine.parse("It's sunny, let's do something outdoors.")
    print("\n--- Sunny outdoors ---")
    print(f"Weather: {u8.weather_context}, Setting: {u8.setting_preference}")

    # 9. "My friend is visiting Cape Town tomorrow. We have R600, neither of us drinks, it's raining, and we need to be home by 10."
    u9 = engine.parse("My friend is visiting Cape Town tomorrow. We have R600, neither of us drinks, it's raining, and we need to be home by 10.")
    print("\n--- Visiting friend multi-constraint ---")
    print(f"People: {u9.people_count}, Budget: {u9.budget_amount}, Weather: {u9.weather_context}, Setting: {u9.setting_preference}, Exclusions: {u9.exclusions}, End: {u9.end_time}, Date: {u9.date_spec}")


def test_redteam_preferences_and_exclusions(engine):
    # 10. "I'd love somewhere quiet, but if that's difficult just give me somewhere nice."
    u10 = engine.parse("I'd love somewhere quiet, but if that's difficult just give me somewhere nice.")
    print("\n--- Soft preference fallback ---")
    print(f"Preferences: {u10.preferences}, Descriptors: {u10.semantic_descriptors}")

    # 11. "Anywhere except loud bars."
    u11 = engine.parse("Anywhere except loud bars.")
    print("\n--- Anywhere except loud bars ---")
    print(f"Exclusions: {u11.exclusions}, Preferences: {u11.preferences}")


def test_redteam_conflicting_constraints(engine):
    # 12. "Fancy dinner for two under R200."
    u12 = engine.parse("Fancy dinner for two under R200.")
    print("\n--- Fancy dinner for two under R200 ---")
    print(f"People: {u12.people_count}, Budget: {u12.budget_amount} ({u12.budget_kind}), Descriptors: {u12.semantic_descriptors}")
    criteria = DecisionCriteria(
        location="Cape Town",
        maximum_cost=u12.budget_amount,
        group_size=u12.people_count,
        semantic_descriptors=u12.semantic_descriptors,
    )
    result = decide(criteria, list(FIXTURE_PLACES), list(FIXTURE_ACTIVITIES))
    print(f"Eligible candidates count: {len(result.eligible)}, Trade-off summary: {result.trade_off_summary}")
