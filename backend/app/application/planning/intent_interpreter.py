import re
from decimal import Decimal
from uuid import UUID

from app.application.planning.dtos import PlanningIntent


class IntentInterpreter:
    def interpret(self, user_id: UUID, raw_request: str) -> PlanningIntent:
        request = raw_request.strip()

        if not request:
            raise ValueError("Planning request cannot be empty.")

        return PlanningIntent(
            user_id=user_id,
            raw_request=request,
            goal=self._extract_goal(request),
            location=self._extract_location(request),
            group_size=self._extract_group_size(request),
            budget_max=self._extract_budget(request),
        )

    @staticmethod
    def _extract_goal(request: str) -> str:
        return request

    @staticmethod
    def _extract_location(request: str) -> str | None:
        match = re.search(
            r"\b(?:in|near|around)\s+([A-Za-z][A-Za-z\s-]*?)(?=\s+(?:for|with|on|this|next)\b|[,.!?]|$)",
            request,
            re.IGNORECASE,
        )

        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_group_size(request: str) -> int:
        match = re.search(
            r"\bwith\s+(\d+)\s+friends?\b",
            request,
            re.IGNORECASE,
        )

        if match:
            return int(match.group(1)) + 1

        match = re.search(
            r"\bfor\s+(\d+)\s+(?:people|persons?)\b",
            request,
            re.IGNORECASE,
        )

        return int(match.group(1)) if match else 1

    @staticmethod
    def _extract_budget(request: str) -> Decimal | None:
        match = re.search(
            r"\bR\s?(\d+(?:[.,]\d{1,2})?)\b",
            request,
            re.IGNORECASE,
        )

        if not match:
            return None

        return Decimal(match.group(1).replace(",", "."))
