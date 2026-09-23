# Product Domain

The planning domain is structured around:

```text
User
  |
  +-- Context (location, timing, group size, transport)
  |
  +-- Preferences & Constraints (budget ceilings, preferences, requirements)
  |
  +-- Plans (lifecycle: draft -> proposed -> ready / archived)
          |
          +-- Understanding Layer (synthesizes context and constraints)
          |
          +-- Information Options (places, activities, services from providers)
          |
          +-- Decision Engine (evaluates fit, produces human explanations)
          |
          +-- Proposed Itinerary ("Here's what I'd do" sequence)
          |         |
          |         +-- Candidate Slots & Trade-off Alternatives
          |
          +-- Plan Items (authoritative persistent selections)
          |
          +-- Budget Calculation (budget limit, total planned, remaining, over-budget flag)
```

## First Product Slice & Understanding Layer

The domain slice proves that the system can:

1. Accept a natural-language intention (*"What are you trying to do?"*).
2. Interpret the request through a structured **Understanding Layer** (`PlanningUnderstandingPort`):
   - Normalizes text and extracts 8 core planning dimensions: goal, occasion, people/group context, date/time window, location semantics, budget semantics, soft preferences, and hard exclusions.
   - Distinguishes explicit user statements from inferred or defaulted context via provenance tracking (`explicit`, `inferred`, `defaulted`, `unknown`).
   - Surfaces ambiguities without turning the interface into an interrogation questionnaire.
3. Present an immediate understanding of the request (*"Got it. Here's what I'm working with"*).
4. Query the information layer for eligible places and activities.
5. Apply decision heuristics to assemble a coherent proposed itinerary (*"Here's what I'd do"*):
   - Strict hard exclusion filtering (e.g. `no_outdoors`, `not_too_fancy`, `no_clubs`).
   - Additive scoring boosts for occasions and soft preferences.
6. Explain decision rationale in human language without exposing machine scores or internals.
7. Allow the user to review, swap alternatives, or remove items with real-time budget updates.
8. Support conversational tweaks (*"Tweak this plan"*, e.g., *"Make it cheaper"*, *"Nothing outdoors"*, *"Add 2 people"*) with context retention via `POST /plans/{id}/modifications`.
9. Persist the chosen plan items via authoritative backend selection upon confirmation (*"Looks good"*).
10. Maintain immutable archived plans and calculated budget invariants in PostgreSQL.