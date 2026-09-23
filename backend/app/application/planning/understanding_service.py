from __future__ import annotations

import re
from decimal import Decimal
from uuid import UUID

from app.application.planning.ports import PlanningUnderstandingPort
from app.domain.entities.planning.information import InformationCategory
from app.domain.entities.planning.understanding import BudgetKind, PlanningUnderstanding, ProvenanceKind


class DeterministicUnderstandingEngine(PlanningUnderstandingPort):
    """Deterministic, provider-agnostic implementation of PlanningUnderstandingPort.

    Implements a multi-stage conversational understanding pipeline that normalizes the request,
    extracts intent, occasion, people/relationship context, date and time windows, location semantics,
    budget semantics, preferences, exclusions, and activity categories without guessing or inventing facts.
    """

    async def understand(self, user_id: UUID, raw_request: str) -> PlanningUnderstanding:
        return self.parse(raw_request)

    def parse(self, raw_request: str) -> PlanningUnderstanding:
        request = raw_request.strip()
        if not request:
            raise ValueError("Planning request cannot be empty.")

        normalized = self._normalize(request)
        provenance: dict[str, str] = {}
        ambiguities: list[str] = []

        # 1. Occasion & relationship context
        occasion, occasion_prov = self._extract_occasion(normalized)
        if occasion:
            provenance["occasion"] = occasion_prov.value
        else:
            provenance["occasion"] = ProvenanceKind.UNKNOWN.value

        # 2. People & group context
        people_count, rel_context, people_prov, people_ambiguities = self._extract_people(normalized, occasion)
        ambiguities.extend(people_ambiguities)
        if people_count is not None:
            provenance["people_count"] = people_prov.value
        else:
            provenance["people_count"] = ProvenanceKind.UNKNOWN.value
        if rel_context:
            provenance["relationship_context"] = people_prov.value

        # 3. Date & time windows
        date_spec, time_window, date_prov, time_ambiguities = self._extract_date_and_time(normalized)
        ambiguities.extend(time_ambiguities)
        if date_spec:
            provenance["date"] = date_prov.value
        else:
            provenance["date"] = ProvenanceKind.UNKNOWN.value
        if time_window:
            provenance["time_window"] = date_prov.value
        else:
            provenance["time_window"] = ProvenanceKind.UNKNOWN.value

        # 4. Location semantics
        location, is_inferred, loc_prov = self._extract_location(normalized)
        provenance["location"] = loc_prov.value

        # 5. Budget semantics
        budget_amount, budget_kind, budget_prov = self._extract_budget(normalized)
        provenance["budget"] = budget_prov.value

        # 6. Exclusions (hard negative constraints)
        exclusions = self._extract_exclusions(normalized)
        if exclusions:
            provenance["exclusions"] = ProvenanceKind.EXPLICIT.value

        # 7. Soft preferences
        preferences = self._extract_preferences(normalized, exclusions)
        if preferences:
            provenance["preferences"] = ProvenanceKind.EXPLICIT.value

        # 8. Activity categories
        activity_types = self._extract_activity_types(normalized, occasion, preferences)
        if activity_types:
            provenance["activity_types"] = ProvenanceKind.INFERRED.value

        # 9. Goal synthesis
        goal = self._extract_goal(normalized, occasion, rel_context)

        return PlanningUnderstanding(
            raw_request=request,
            goal=goal,
            occasion=occasion,
            people_count=people_count,
            relationship_context=rel_context,
            date_spec=date_spec,
            time_window=time_window,
            location=location,
            location_is_inferred=is_inferred,
            budget_amount=budget_amount,
            budget_kind=budget_kind,
            preferences=tuple(preferences),
            exclusions=tuple(exclusions),
            activity_types=tuple(activity_types),
            ambiguities=tuple(ambiguities),
            provenance=provenance,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        # Standardize quotes, hyphens, and whitespace
        normalized = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
        return " ".join(normalized.split())

    @staticmethod
    def _extract_occasion(text: str) -> tuple[str | None, ProvenanceKind]:
        lower = text.lower()
        if re.search(r"\b(?:date night|romantic|anniversary|on a date|for a date)\b", lower):
            return "date", ProvenanceKind.EXPLICIT
        if re.search(r"\b(?:take|taking|with|for)\s+my\s+(?:boyfriend|girlfriend|partner|husband|wife)\b", lower):
            return "date", ProvenanceKind.INFERRED
        if re.search(r"\b(?:birthday|bday|b-day)\b", lower):
            return "birthday", ProvenanceKind.EXPLICIT
        if re.search(r"\b(?:celebration|celebrate|promotion|milestone|party)\b", lower):
            return "celebration", ProvenanceKind.EXPLICIT
        if re.search(r"\b(?:girls'? day|girls'? night|boys'? night|(?:with|and)\s+(?:my |\d+\s+)?(?:friends|mates)|\b\d+\s+friends\b|\bfriends\b)\b", lower):
            return "friends", ProvenanceKind.EXPLICIT
        if re.search(r"\b(?:family|with the kids|with parents|for my mom|with my mom|for my dad|with my dad)\b", lower):
            return "family", ProvenanceKind.EXPLICIT
        if re.search(r"\b(?:just me|solo|by myself|alone|self[ -]?care)\b", lower):
            return "solo", ProvenanceKind.EXPLICIT
        if re.search(r"\b(?:hangout|hang out|casual catchup|catch up)\b", lower):
            return "casual_hangout", ProvenanceKind.EXPLICIT
        return None, ProvenanceKind.UNKNOWN

    @staticmethod
    def _extract_people(
        text: str, occasion: str | None
    ) -> tuple[int | None, str | None, ProvenanceKind, list[str]]:
        lower = text.lower()
        ambiguities: list[str] = []

        # Explicit couple references
        match_partner = re.search(r"\b(?:take|taking|with|for)\s+my\s+(boyfriend|girlfriend|partner|husband|wife)\b", lower)
        if match_partner:
            rel = match_partner.group(1)
            return 2, rel, ProvenanceKind.INFERRED, ambiguities

        # Family references (e.g. for my mom)
        match_family_rel = re.search(r"\b(?:for|with)\s+my\s+(mom|mother|dad|father|sister|brother)\b", lower)
        if match_family_rel:
            rel = match_family_rel.group(1)
            return 2, rel, ProvenanceKind.INFERRED, ambiguities

        if re.search(r"\b(?:me and my (?:boyfriend|girlfriend|partner|husband|wife|friend))\b", lower):
            rel = "boyfriend" if "boyfriend" in lower else "partner"
            if "girlfriend" in lower:
                rel = "girlfriend"
            elif "friend" in lower:
                rel = "friends"
            return 2, rel, ProvenanceKind.EXPLICIT, ambiguities

        # "me and N friends" / "with N friends" -> N + 1
        match_friends_count = re.search(r"\b(?:me and|with)\s+(\d+)\s+friends?\b", lower)
        if match_friends_count:
            return int(match_friends_count.group(1)) + 1, "friends", ProvenanceKind.EXPLICIT, ambiguities

        if re.search(r"\b(?:the two of us|both of us|for two|for 2)\b", lower):
            return 2, "couple" if occasion == "date" else "pair", ProvenanceKind.EXPLICIT, ambiguities

        # Solo
        if re.search(r"\b(?:just me|solo|by myself|alone)\b", lower):
            return 1, "solo", ProvenanceKind.EXPLICIT, ambiguities

        # with N friends -> N + 1
        with_friends = re.search(r"\bwith\s+(\d+)\s+friends?\b", lower)
        if with_friends:
            return int(with_friends.group(1)) + 1, "friends", ProvenanceKind.EXPLICIT, ambiguities

        # for N people / persons
        for_people = re.search(r"\bfor\s+(\d+)\s+(?:people|persons?)\b", lower)
        if for_people:
            return int(for_people.group(1)), "group", ProvenanceKind.EXPLICIT, ambiguities

        # group of N
        group_of = re.search(r"\bgroup\s+of\s+(\d+)\b", lower)
        if group_of:
            return int(group_of.group(1)), "group", ProvenanceKind.EXPLICIT, ambiguities

        # "with my friends" / "with friends" without a count
        if re.search(r"\b(?:with my friends|with friends|with mates)\b", lower):
            ambiguities.append("Exact group size not specified ('with friends'); planning with flexible group options.")
            return None, "friends", ProvenanceKind.EXPLICIT, ambiguities

        # Default fallback if occasion is date
        if occasion == "date":
            return 2, "couple", ProvenanceKind.INFERRED, ambiguities

        ambiguities.append("Group size not specified; defaulting to single or flexible group options.")
        return None, None, ProvenanceKind.UNKNOWN, ambiguities

    @staticmethod
    def _extract_date_and_time(
        text: str,
    ) -> tuple[str | None, str | None, ProvenanceKind, list[str]]:
        lower = text.lower()
        ambiguities: list[str] = []

        date_spec: str | None = None
        time_window: str | None = None
        prov = ProvenanceKind.UNKNOWN

        # Days of week
        for day in ("saturday", "sunday", "friday", "thursday", "wednesday", "tuesday", "monday"):
            if re.search(rf"\b{day}\b", lower):
                date_spec = day.capitalize()
                prov = ProvenanceKind.EXPLICIT
                break

        if not date_spec:
            if re.search(r"\bthis weekend|the weekend\b", lower):
                date_spec = "This weekend"
                prov = ProvenanceKind.EXPLICIT
            elif re.search(r"\bnext weekend\b", lower):
                date_spec = "Next weekend"
                prov = ProvenanceKind.EXPLICIT
            elif re.search(r"\btomorrow\b", lower):
                date_spec = "Tomorrow"
                prov = ProvenanceKind.EXPLICIT
            elif re.search(r"\btoday|tonight\b", lower):
                date_spec = "Today"
                prov = ProvenanceKind.EXPLICIT

        # Time windows
        if re.search(r"\b(?:morning|breakfast)\b", lower):
            time_window = "morning"
        elif re.search(r"\b(?:afternoon|lunchtime|lunch)\b", lower):
            time_window = "afternoon"
        elif re.search(r"\b(?:evening|dinner time|dinner)\b", lower):
            time_window = "evening"
        elif re.search(r"\b(?:night|tonight|late night)\b", lower):
            time_window = "night"
        elif re.search(r"\bafter work\b", lower):
            time_window = "after_work"
        elif re.search(r"\ball day\b", lower):
            time_window = "all_day"

        if date_spec and not time_window:
            ambiguities.append(f"Specific time window on {date_spec} not stated; planning for a flexible schedule.")

        return date_spec, time_window, prov, ambiguities

    @staticmethod
    def _extract_location(text: str) -> tuple[str, bool, ProvenanceKind]:
        lower = text.lower()

        # Explicit known neighborhoods
        neighborhood_map = {
            "sea point": "Sea Point",
            "camps bay": "Camps Bay",
            "v&a": "Waterfront",
            "waterfront": "Waterfront",
            "bo-kaap": "Bo-Kaap",
            "gardens": "Gardens",
            "kloof street": "Kloof Street",
            "bree street": "Bree Street",
            "constantia": "Constantia",
            "green point": "Green Point",
        }
        for token, loc_name in neighborhood_map.items():
            if re.search(rf"\b{token}\b", lower):
                return loc_name, False, ProvenanceKind.EXPLICIT

        # Explicit mention of Cape Town
        if re.search(r"\b(?:in|near|around)\s+cape town\b", lower):
            return "Cape Town", False, ProvenanceKind.EXPLICIT

        # Conversational / inferred city references
        if re.search(r"\b(?:around town|in town|central|somewhere central|city bowl|near town|close by)\b", lower):
            return "Cape Town", True, ProvenanceKind.INFERRED

        # General pattern "in [Location]"
        match = re.search(
            r"\b(?:in|near|around)\s+([A-Za-z][A-Za-z\s-]*?)(?=\s+(?:for|with|on|this|next|around|maybe|under)\b|[,.!?]|$)",
            text,
            re.IGNORECASE,
        )
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in {"town", "a date", "the mood"}:
                return candidate, False, ProvenanceKind.EXPLICIT

        # Default context
        return "Cape Town", True, ProvenanceKind.DEFAULTED

    @staticmethod
    def _extract_budget(text: str) -> tuple[Decimal | None, BudgetKind, ProvenanceKind]:
        lower = text.lower()

        # Free / zero cost
        if re.search(r"\b(?:free|zero cost|no money|no budget)\b", lower):
            return Decimal("0"), BudgetKind.HARD_MAX, ProvenanceKind.EXPLICIT

        # Explicit numeric budget extraction (R800, R 800, 800 rand, 800 bucks)
        match = re.search(r"\bR\s?(\d+(?:[.,]\d{1,2})?)\b", text, re.IGNORECASE)
        if not match:
            match = re.search(r"\b(\d+(?:[.,]\d{1,2})?)\s*(?:rand|bucks)\b", text, re.IGNORECASE)

        if match:
            amount = Decimal(match.group(1).replace(",", "."))
            # Determine semantics
            if re.search(r"\b(?:under|max|maximum|at most|up to|cap at|limit)\s*(?:r|rand|bucks)?\s*\d+", lower):
                return amount, BudgetKind.HARD_MAX, ProvenanceKind.EXPLICIT
            if re.search(r"\b(?:maybe|around|about|roughly|approx|approx\.|~)\s*(?:r|rand|bucks)?\s*\d+", lower):
                return amount, BudgetKind.APPROXIMATE, ProvenanceKind.EXPLICIT
            # Conversational single amount defaults to approximate
            return amount, BudgetKind.APPROXIMATE, ProvenanceKind.EXPLICIT

        # Qualitative budget preference without exact number
        if re.search(r"\b(?:cheap|affordable|budget[ -]friendly|on a budget|not expensive|not too expensive|nothing too expensive|nothing expensive)\b", lower):
            return None, BudgetKind.PREFERENCE, ProvenanceKind.EXPLICIT

        return None, BudgetKind.NONE, ProvenanceKind.UNKNOWN

    @staticmethod
    def _extract_exclusions(text: str) -> list[str]:
        lower = text.lower()
        exclusions: list[str] = []

        if re.search(r"\b(?:nothing too fancy|not too fancy|nothing fancy|not fancy|don't want anything fancy|no fancy)\b", lower):
            exclusions.append("not_too_fancy")

        if re.search(r"\b(?:no outdoor|no outdoors|nothing outdoors|not outdoors|avoid outdoors|no nature)\b", lower):
            exclusions.append("no_outdoors")

        if re.search(r"\b(?:no clubs|no clubbing|no nightlife|no party|no parties)\b", lower):
            exclusions.append("no_clubs")

        if re.search(r"\b(?:not too expensive|nothing expensive|no expensive places)\b", lower):
            exclusions.append("nothing_expensive")

        if re.search(r"\b(?:no walking|minimal walking|avoid walking)\b", lower):
            exclusions.append("minimal_walking")

        return exclusions

    @staticmethod
    def _extract_preferences(text: str, exclusions: list[str]) -> list[str]:
        lower = text.lower()
        preferences: list[str] = []

        if "not_too_fancy" not in exclusions:
            if re.search(r"\b(?:fancy|upscale|fine dining|high end)\b", lower):
                preferences.append("fancy")

        if re.search(r"\b(?:somewhere nice|nice place|something nice|nice)\b", lower):
            preferences.append("nice")

        if re.search(r"\b(?:casual|chill|relaxed|laid back|unhurried|easygoing)\b", lower):
            preferences.append("casual")

        if re.search(r"\b(?:fun|something fun|exciting|entertaining|adventurous)\b", lower):
            preferences.append("fun")

        if re.search(r"\b(?:romantic|intimate|cozy|cute)\b", lower):
            preferences.append("romantic")

        if re.search(r"\b(?:food[ -]focused|foodie|good food|great food|delicious|tasting)\b", lower):
            preferences.append("food_focused")

        if re.search(r"\b(?:aesthetic|scenic|pretty|view)\b", lower):
            preferences.append("aesthetic")

        if "no_outdoors" not in exclusions:
            if re.search(r"\b(?:outdoors|nature|in the sun|open air)\b", lower):
                preferences.append("outdoors")

        if re.search(r"\b(?:cultural|culture|historic|history|museum|artsy)\b", lower):
            preferences.append("cultural")

        return preferences

    @staticmethod
    def _extract_activity_types(
        text: str, occasion: str | None, preferences: list[str]
    ) -> list[InformationCategory]:
        lower = text.lower()
        categories: list[InformationCategory] = []

        if re.search(r"\b(?:food|eat|dinner|lunch|breakfast|brunch|tasting|drinks|cocktail|restaurant|cafe|coffee)\b", lower) or "food_focused" in preferences:
            categories.append(InformationCategory.FOOD)

        if re.search(r"\b(?:walk|hike|park|garden|nature|beach|scenic)\b", lower) or "outdoors" in preferences:
            categories.append(InformationCategory.NATURE)

        if re.search(r"\b(?:culture|cultural|history|museum|art|heritage|guided)\b", lower) or "cultural" in preferences:
            categories.append(InformationCategory.CULTURE)

        if re.search(r"\b(?:movie|theatre|theater|show|music|live|comedy|entertainment)\b", lower):
            categories.append(InformationCategory.ENTERTAINMENT)

        if re.search(r"\b(?:spa|massage|wellness|relax)\b", lower):
            categories.append(InformationCategory.WELLNESS)

        if re.search(r"\b(?:market|shopping|mall|boutique)\b", lower):
            categories.append(InformationCategory.SHOPPING)

        if re.search(r"\b(?:fun|entertainment|activity|activities)\b", lower) or "fun" in preferences:
            for cat in (InformationCategory.FOOD, InformationCategory.NATURE, InformationCategory.CULTURE):
                if cat not in categories:
                    categories.append(cat)

        # If date, social outing, or celebration and no explicit activity stated, food is natural default
        if not categories and occasion in {"date", "friends", "casual_hangout", "birthday", "celebration", "family"}:
            categories.append(InformationCategory.FOOD)

        return categories

    @staticmethod
    def _extract_goal(text: str, occasion: str | None, rel: str | None) -> str:
        # Formulate a crisp, human-facing goal description
        if occasion == "date":
            partner = rel if rel in {"boyfriend", "girlfriend", "partner", "husband", "wife"} else "partner"
            return f"Plan a date with {partner}"
        if occasion == "birthday":
            if rel in {"mom", "mother", "dad", "father", "friend", "partner"}:
                return f"Plan a birthday celebration for {rel}"
            return "Plan a birthday celebration"
        if occasion == "celebration":
            return "Plan a celebration outing"
        if occasion == "friends":
            return "Plan an outing with friends"
        if occasion == "solo":
            return "Plan a solo outing"
        return text
