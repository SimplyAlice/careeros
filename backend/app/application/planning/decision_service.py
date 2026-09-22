from __future__ import annotations

from app.application.planning.information import OptionSearchCriteria, PlanningInformationService
from app.domain.entities.planning.decision import DecisionCriteria, DecisionResult
from app.domain.entities.planning.decision_engine import decide


class PlanningDecisionService:
    """Produces deterministic, explainable candidate decisions.

    Depends only on the application-level `PlanningInformationService`
    (itself backed by the `PlanningInformationProvider` port), never on a
    concrete provider. Nothing is persisted: the engine only evaluates and
    ranks options for the caller to choose from.
    """

    def __init__(self, information: PlanningInformationService) -> None:
        self._information = information

    async def recommend(self, criteria: DecisionCriteria) -> DecisionResult:
        search = _search_criteria(criteria)
        places = await self._information.search_places(search)
        activities = await self._information.search_activities(search)
        result = decide(criteria, places, activities)
        # Provenance is the provider's authoritative source, not inferred
        # from individual entities, so callers always see one consistent
        # answer about whether the data is live or a fixture.
        return DecisionResult(candidates=result.candidates, source=self._information.source.data_source)


def _search_criteria(criteria: DecisionCriteria) -> OptionSearchCriteria:
    """Reuse the existing option-search concept for the provider query.

    Only location and category are pushed down to the provider as a narrow
    pre-filter. Budget, group size, and duration are deliberately *not*
    pushed down: if the provider removed those options the engine could
    never explain why they were excluded, which is the core purpose of the
    decision layer. The engine therefore evaluates the hard constraints
    itself and produces eligible and ineligible candidates with reasons.
    """
    return OptionSearchCriteria(location=criteria.location, category=criteria.category)
