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
        (
            date_spec,
            time_window,
            start_time,
            end_time,
            time_confidence,
            duration_limit,
            date_prov,
            time_prov,
            time_ambiguities,
        ) = self._extract_date_and_time(normalized)
        ambiguities.extend(time_ambiguities)
        if date_spec:
            provenance["date"] = date_prov.value
        else:
            provenance["date"] = ProvenanceKind.UNKNOWN.value
        if time_window:
            provenance["time_window"] = time_prov.value
        else:
            provenance["time_window"] = ProvenanceKind.UNKNOWN.value
        if start_time:
            provenance["start_time"] = time_prov.value
        if end_time:
            provenance["end_time"] = time_prov.value
        if duration_limit:
            provenance["duration_limit"] = ProvenanceKind.EXPLICIT.value

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
            start_time=start_time,
            end_time=end_time,
            time_confidence=time_confidence,
            duration_limit_minutes=duration_limit,
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

        # Check for relationship mention
        rel: str | None = None
        match_partner = re.search(r"\b(?:take|taking|with|for)\s+my\s+(boyfriend|girlfriend|partner|husband|wife)\b", lower)
        if match_partner:
            rel = match_partner.group(1)

        match_family_rel = re.search(r"\b(?:(?:for|with)\s+my|my)\s+(mom|mother|dad|father|sister|brother)(?:'s|\b)", lower)
        if match_family_rel:
            rel = match_family_rel.group(1)

        # 1. "me and N friends" / "with N friends" -> N + 1
        match_friends_count = re.search(r"\b(?:me and|with)\s+(\d+)\s+friends?\b", lower)
        if match_friends_count:
            return int(match_friends_count.group(1)) + 1, "friends", ProvenanceKind.EXPLICIT, ambiguities

        # 2. Explicit people counts: "maybe 3 people", "about 4 people", "for 5 people", "for four people"
        word_to_num = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        match_people_count = re.search(
            r"\b(?:(?:maybe|around|about|for)\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:people|persons?|guests?)\b",
            lower,
        )
        if match_people_count:
            raw_cnt = match_people_count.group(1)
            parsed_count = word_to_num.get(raw_cnt, int(raw_cnt) if raw_cnt.isdigit() else None)
            if parsed_count is not None:
                return parsed_count, rel or "group", ProvenanceKind.EXPLICIT, ambiguities

        # 3. group of N
        group_of = re.search(r"\bgroup\s+of\s+(\d+)\b", lower)
        if group_of:
            return int(group_of.group(1)), rel or "group", ProvenanceKind.EXPLICIT, ambiguities

        # 4. Explicit couple / pair references
        if re.search(r"\b(?:me and my (?:boyfriend|girlfriend|partner|husband|wife|friend))\b", lower):
            pair_rel = "boyfriend" if "boyfriend" in lower else "partner"
            if "girlfriend" in lower:
                pair_rel = "girlfriend"
            elif "friend" in lower:
                pair_rel = "friends"
            return 2, pair_rel, ProvenanceKind.EXPLICIT, ambiguities

        if re.search(r"\b(?:the two of us|both of us|for two|for 2)\b", lower):
            return 2, "couple" if occasion == "date" else "pair", ProvenanceKind.EXPLICIT, ambiguities

        # 5. Partner or family inferred pair (default to 2 if no explicit count given)
        if match_partner:
            return 2, rel, ProvenanceKind.INFERRED, ambiguities

        if match_family_rel:
            return 2, rel, ProvenanceKind.INFERRED, ambiguities

        # 6. Solo
        if re.search(r"\b(?:just me|solo|by myself|alone)\b", lower):
            return 1, "solo", ProvenanceKind.EXPLICIT, ambiguities

        # 7. "with my friends" / "with friends" without a count
        if re.search(r"\b(?:with my friends|with friends|with mates)\b", lower):
            ambiguities.append("Exact group size not specified ('with friends'); planning with flexible group options.")
            return None, "friends", ProvenanceKind.EXPLICIT, ambiguities

        # Default fallback if occasion is date
        if occasion == "date":
            return 2, "couple", ProvenanceKind.INFERRED, ambiguities

        ambiguities.append("Group size not specified; defaulting to single or flexible group options.")
        return None, None, ProvenanceKind.UNKNOWN, ambiguities

    @staticmethod
    def _normalize_clock_time(time_val: str, meridiem: str | None = None, is_deadline: bool = False) -> str:
        if ":" in time_val:
            parts = time_val.split(":")
            h, m = int(parts[0]), int(parts[1])
        else:
            h, m = int(time_val), 0

        if meridiem == "pm" and h < 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        elif meridiem is None:
            if is_deadline:
                if 1 <= h <= 11:
                    h += 12
            else:
                if 1 <= h <= 6:
                    h += 12

        return f"{h:02d}:{m:02d}"

    @staticmethod
    def _extract_date_and_time(
        text: str,
    ) -> tuple[
        str | None,
        str | None,
        str | None,
        str | None,
        str,
        int | None,
        ProvenanceKind,
        ProvenanceKind,
        list[str],
    ]:
        lower = text.lower()
        ambiguities: list[str] = []

        date_spec: str | None = None
        time_window: str | None = None
        start_time: str | None = None
        end_time: str | None = None
        time_confidence = "unknown"
        duration_limit_minutes: int | None = None
        date_prov = ProvenanceKind.UNKNOWN
        time_prov = ProvenanceKind.UNKNOWN

        # 1. Days of week / relative dates
        for day in ("saturday", "sunday", "friday", "thursday", "wednesday", "tuesday", "monday"):
            if re.search(rf"\b{day}\b", lower):
                date_spec = day.capitalize()
                date_prov = ProvenanceKind.EXPLICIT
                break

        if not date_spec:
            if re.search(r"\bthis weekend|the weekend\b", lower):
                date_spec = "This weekend"
                date_prov = ProvenanceKind.EXPLICIT
            elif re.search(r"\bnext weekend\b", lower):
                date_spec = "Next weekend"
                date_prov = ProvenanceKind.EXPLICIT
            elif re.search(r"\btomorrow\b", lower):
                date_spec = "Tomorrow"
                date_prov = ProvenanceKind.EXPLICIT
            elif re.search(r"\btoday|tonight\b", lower):
                date_spec = "Today"
                date_prov = ProvenanceKind.EXPLICIT

        # 2. Duration limit
        num_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
        }
        m_dur = re.search(r"\b(?:only have|have|for)\s+(\d+|one|two|three|four|five|six)\s+hours?\b", lower)
        if not m_dur:
            m_dur = re.search(r"\b(\d+|one|two|three|four|five|six)\s+hours?\b", lower)
        if m_dur:
            dur_val = m_dur.group(1).lower()
            hours_count = num_map.get(dur_val) or (int(dur_val) if dur_val.isdigit() else None)
            if hours_count:
                duration_limit_minutes = hours_count * 60
                ambiguities.append(f"Itinerary time constraint: limited to approximately {hours_count} hours.")

        # 3. Time spans and start/end clock times
        m_span = re.search(
            r"\bfrom\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?\s+to\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?\b",
            lower,
        )
        if m_span:
            start_time = DeterministicUnderstandingEngine._normalize_clock_time(m_span.group(1), m_span.group(2))
            end_time = DeterministicUnderstandingEngine._normalize_clock_time(m_span.group(3), m_span.group(4), is_deadline=True)
            time_confidence = "exact"
            time_prov = ProvenanceKind.EXPLICIT
            time_window = f"{start_time}-{end_time}"
        else:
            m_start_approx = re.search(
                r"\b(?:start\s+around|start\s+about|around|about|approx(?:imately)?)\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?\b",
                lower,
            )
            m_start_exact = re.search(r"\b(?:start\s+at|at)\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?\b", lower)

            if m_start_approx:
                start_time = DeterministicUnderstandingEngine._normalize_clock_time(m_start_approx.group(1), m_start_approx.group(2))
                time_confidence = "approximate"
                time_prov = ProvenanceKind.EXPLICIT
                ambiguities.append(f"Start time is approximate (~{start_time}); scheduled with flexibility.")
            elif m_start_exact:
                start_time = DeterministicUnderstandingEngine._normalize_clock_time(m_start_exact.group(1), m_start_exact.group(2))
                time_confidence = "exact"
                time_prov = ProvenanceKind.EXPLICIT

            m_end = re.search(
                r"\b(?:until|to|home by|be home by|finish by|by)\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?\b",
                lower,
            )
            if m_end:
                end_time = DeterministicUnderstandingEngine._normalize_clock_time(m_end.group(1), m_end.group(2), is_deadline=True)
                time_prov = ProvenanceKind.EXPLICIT
                ambiguities.append(f"Requested end time: home/done by {end_time}.")

        # 4. Period keywords
        period: str | None = None
        if re.search(r"\b(?:morning|breakfast)\b", lower):
            period = "morning"
        elif re.search(r"\b(?:afternoon|lunchtime|lunch)\b", lower):
            period = "afternoon"
        elif re.search(r"\b(?:evening|dinner time|dinner)\b", lower):
            period = "evening"
        elif re.search(r"\b(?:night|tonight|late night)\b", lower):
            period = "night"
        elif re.search(r"\bafter work\b", lower):
            period = "after_work"
        elif re.search(r"\ball day|whole day\b", lower):
            period = "all_day"

        if start_time and end_time:
            time_window = f"{start_time}-{end_time}"
        elif period and not start_time and not end_time:
            time_window = period
            time_confidence = "inferred"
            time_prov = ProvenanceKind.INFERRED
            if period == "morning":
                start_time = "09:00"
                end_time = "12:30"
            elif period == "afternoon":
                start_time = "12:30"
                end_time = "17:30"
            elif period == "evening":
                start_time = "18:00"
                end_time = "22:00"
            elif period == "night":
                start_time = "20:00"
                end_time = "23:30"
            elif period == "after_work":
                start_time = "17:30"
                end_time = "21:30"
            elif period == "all_day":
                start_time = "09:00"
                end_time = "20:00"
        elif period and start_time and not end_time:
            time_window = period
            if period == "morning":
                end_time = "12:30"
            elif period == "afternoon":
                end_time = "17:30"
            elif period in {"evening", "night"}:
                end_time = "22:00"
        elif start_time and not time_window:
            time_window = f"from_{start_time}"

        if date_spec and not time_window and not start_time:
            ambiguities.append(f"Specific time window on {date_spec} not stated; planning for a flexible schedule.")

        return (
            date_spec,
            time_window,
            start_time,
            end_time,
            time_confidence,
            duration_limit_minutes,
            date_prov,
            time_prov,
            ambiguities,
        )

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

        # Explicit numeric budget extraction (R800, R2,000, R 800, 800 rand, 800 bucks)
        match = re.search(r"\bR\s?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b", text, re.IGNORECASE)
        if not match:
            match = re.search(r"\b(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(?:rand|bucks)\b", text, re.IGNORECASE)

        if match:
            amount = Decimal(match.group(1).replace(",", ""))
            # Determine semantics
            if re.search(r"\b(?:under|max|maximum|at most|up to|cap at|limit)\s*(?:r|rand|bucks)?\s*[\d,]+", lower):
                return amount, BudgetKind.HARD_MAX, ProvenanceKind.EXPLICIT
            if re.search(r"\b(?:maybe|around|about|roughly|approx|approx\.|~)\s*(?:r|rand|bucks)?\s*[\d,]+", lower):
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
