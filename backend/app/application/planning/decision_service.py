from __future__ import annotations

from app.application.planning.information import OptionSearchCriteria, PlanningInformationService
from app.domain.entities.planning.decision import DecisionCandidate, DecisionCriteria, DecisionResult
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
        attr = self._information.source.attribution
        candidates = [
            DecisionCandidate(
                option_id=c.option_id,
                option_type=c.option_type,
                name=c.name,
                is_eligible=c.is_eligible,
                score=c.score,
                reasons=c.reasons,
                category=c.category,
                cost=c.cost,
                duration_minutes=c.duration_minutes,
                location=c.location,
                source=c.source,
                address=c.address,
                opening_hours=c.opening_hours,
                freshness=c.freshness,
                verified_at=c.verified_at,
                attribution=c.attribution or attr,
            )
            for c in result.candidates
        ]
        return DecisionResult(
            candidates=tuple(candidates),
            source=self._information.source.data_source,
            is_live=self._information.source.is_live,
            attribution=attr,
            freshness=self._information.source.freshness,
        )


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
