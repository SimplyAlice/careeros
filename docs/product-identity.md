# Project Identity: Dayform

**Dayform** is an intelligent real-world planning platform.

> **Give shape to your day.**  
> *“Tell me what you want to do. I’ll figure out the rest.”*

The product helps people turn an intention into an actionable, coherent plan.

Instead of forcing users to search across maps, transport apps, restaurant sites,
social media, event pages, shopping platforms, and other fragmented sources,
the system combines relevant information with the user's context and constraints.

The unit of value is a **PLAN**, not a search result or a directory listing.

## Product Scope

Dayform conceptually supports a wide variety of real-world planning situations:

- **Social Outings**: Planning a fun day or night out with friends
- **Dates**: Curating a romantic, memorable outing within a budget
- **Birthdays & Celebrations**: Assembling a special celebration experience
- **Food & Dining**: Finding restaurants, food markets, or tasting experiences
- **Activities & Culture**: Discovering walks, tours, museums, and entertainment
- **Shopping & Wellness**: Combining appointments, shopping, and self-care
- **Short Trips**: Day trips and weekend excursions
- **General Intentions**: Answering *"I want to do something nice this weekend"*

Users never have to choose a rigid category before typing. The primary interaction
remains conversational and natural:

> "What are you trying to do?"

## Core Product Loop

```text
USER INTENTION ("Tell me what you want to do...")
      |
      v
UNDERSTAND CONTEXT & INTENT (Occasion, group, date/time, budget, preferences, exclusions)
      |
      v
FIND RELEVANT INFORMATION (Places, activities, providers)
      |
      v
MAKE DECISIONS (Exclusion filtering, preference scoring, trade-offs, human rationale)
      |
      v
PROPOSE COHERENT PLAN ("Here's what I'd do")
      |
      v
USER REVIEWS & TWEAKS (Swap, remove, conversational adjustments: "Make it cheaper", "No outdoors")
      |
      v
CONFIRMATION ("Looks good" -> Authoritative persistence)
      |
      v
SAVED PLAN (Persistent plan ownership)
      |
      v
EXECUTION ACTIONS (One-tap directions in Google Maps, direct phone calls, venue links, item completion)
      |
      v
LIVE INTELLIGENCE & ADAPTATION (Real-time weather and hours monitoring, non-destructive schedule adaptation)
```