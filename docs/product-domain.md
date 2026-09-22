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

## First Product Slice

The domain slice proves that the system can:

1. Accept a natural-language intention (*"What are you trying to do?"*).
2. Infer relevant context and constraints (location, group size, budget).
3. Present an immediate understanding of the request (*"Got it. Here's what I'm working with"*).
4. Query the information layer for eligible places and activities.
5. Apply decision heuristics to assemble a coherent proposed itinerary (*"Here's what I'd do"*).
6. Explain decision rationale in human language without exposing machine scores or internals.
7. Allow the user to review, swap alternatives, or remove items with real-time budget updates.
8. Persist the chosen plan items via authoritative backend selection upon confirmation (*"Looks good"*).
9. Maintain immutable archived plans and calculated budget invariants in PostgreSQL.