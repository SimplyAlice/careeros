<div align="center">

<img src=".github/readme/hero.svg" alt="Dayform — Give shape to your day" width="100%" />

<br/><br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-6.0+-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

<br/>

**“Tell me what you want to do. I’ll figure out the rest.”**  
*Give shape to your day.*

</div>

---

## What is Dayform?

**Dayform** is an intelligent real-world planning system. It takes an unstructured, natural-language human intention and synthesizes it into an actionable, coherent, budget-aware, and time-sequenced day out.

Whether it is a romantic anniversary dinner, a group birthday celebration, a Saturday cultural outing, an afternoon of self-care, or a spontaneous *"I want to do something fun tonight"*, Dayform connects intention to physical reality.

It is **not** a search engine, a bookmark collector, or a directory of sponsored links.  
Dayform evaluates real venues, verified operating hours, travel buffers, group dynamics, and financial limits to produce **a complete, living plan**.

---

## The Core Loop

Dayform operates through a deterministic six-stage planning lifecycle:

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  INTENTION   │ ──► │  UNDERSTAND  │ ──► │   RESEARCH   │
└──────────────┘     └──────────────┘     └──────────────┘
  Natural human        Extracts group,      Verifies places,
  voice or text        budget ceiling,      operating hours,
  ("Saturday dinner    temporal window,     categories via
   under R1200")       hard exclusions      OpenStreetMap
                             │
                             ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   EXECUTE    │ ◄── │    ADAPT     │ ◄── │     PLAN     │
└──────────────┘     └──────────────┘     └──────────────┘
  Maps directions,     Dynamic shifts       Sequences dwell
  phone calls,         for weather alerts   times, transit,
  calendar export,     or late arrivals     budget headroom
  stop completion      with clean diffs     & trade-offs
```

1. **Intention**: Speak or type naturally without filling out rigid filter forms.
2. **Understand**: Synthesizes the request into structured constraints, distinguishing hard boundaries (*"no seafood"*, *"strict R500 max"*) from soft aesthetic cues (*"romantic"*, *"casual"*).
3. **Research**: Discovers candidate venues with authentic geographical coordinates, street addresses, and verified operating hours via OpenStreetMap and Overpass.
4. **Plan**: Sequences stops in chronological order, computes travel times and dwell buffers, and validates financial headroom.
5. **Adapt**: When reality shifts (*"We're running 45 minutes late"* or sudden rain), recalculates schedules with non-destructive diffs that preserve unaffected stops.
6. **Execute**: Connects directly to the physical world with one-tap Google Maps routing, venue phone dialing, and `.ics` calendar sync.

---

## Why Dayform Exists

Organizing a real outing is broken. Putting together a simple afternoon or evening typically forces you to juggle dozens of browser tabs and mobile apps:

| Traditional Friction | The Dayform Experience |
| :--- | :--- |
| **Search engines** return thousands of sponsored listicles and outdated blog posts. | **Deterministic engine** selects venues that directly satisfy your specific constraints. |
| **Map apps** display isolated pins with zero understanding of sequence or budget pacing. | **Paced itinerary** calculates realistic transit times and comfortable dwell buffers between stops. |
| **Static directories** bury opening hours and dietary options behind clunky interfaces. | **Verified operational rules** ensure you never arrive at a locked door or closed kitchen. |
| **Messaging apps & spreadsheets** become messy scratchpads for computing total spend. | **Real-time budget ledger** tracks per-person costs, group totals, and remaining financial headroom. |

> A collection of saved pins is not a plan. Real plans require understanding who is going, what things cost, when venues actually operate, and what happens when timing changes.

---

## What It Can Do

Dayform supports any real-world human plan:

- **Dates & Anniversaries**: Intimate cocktail lounges, scenic viewpoints, curated dinners, and timed reservations.
- **Group Celebrations**: Birthdays, bachelor/bachelorette gatherings, and family outings accommodating large parties and diverse dietary requirements.
- **Cultural & Weekend Outings**: Art galleries, botanical gardens, live jazz, and coastal walks sequenced by geographical proximity.
- **Self-Care & Shopping**: Spa appointments, boutique shopping districts, and artisanal coffee stops with relaxed pacing.
- **Spontaneous Plans**: *"It's 7:00 PM, I'm in Gardens with R300, what can I do right now?"*

---

## Product Experience

### 1. Conversational Understanding
Express intent in natural words. Dayform extracts temporal windows, group sizes, budget limits, and negative exclusions with transparent confidence ratings.

### 2. Candidate Swapping & Trade-Offs
Every stop is customizable. Browse categorized alternative venues with instant cost trade-off notes before confirming substitutions.

### 3. Non-Destructive Adaptation
When circumstances shift, Dayform recalculates the itinerary without obliterating unaffected plans. You review an exact before-and-after diff highlighting shifted start times and modified stops.

### 4. Real-World Execution
- **One-Tap Directions**: Immediate navigation via Google Maps coordinates.
- **Direct Calling**: Immediate telephone dialer links for reservations and inquiries.
- **Calendar Integration**: One-click download of `.ics` calendar events signed by Dayform.
- **Active Progress Tracking**: Mark stops as complete as your day unfolds.

---

## Technical Architecture

Dayform is designed according to **Clean Architecture** principles, enforcing strict decoupling between domain rules, application services, and external providers:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Frontend (React / Vite)                         │
│   Cinematic Scrollytelling · Real-Time Planning Stage · Adaptive Diff  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Application Layer                        │
│        Endpoints: /api/v1/auth · /planning/requests · /adapt · /actions│
└──────────────────┬──────────────────────────────────┬──────────────────┘
                   │                                  │
┌──────────────────▼──────────────────┐   ┌───────────▼──────────────────┐
│        Application Services         │   │      Domain Planning Engine  │
│  Planning · Adaptation · Execution  │   │  Understanding · Decisions   │
│      Live Intelligence Service      │   │  Temporal Logic · Invariants │
└──────────────────┬──────────────────┘   └───────────┬──────────────────┘
                   │                                  │
┌──────────────────▼──────────────────────────────────▼──────────────────┐
│                   Infrastructure & External Providers                  │
│   PostgreSQL (Asyncpg / Alembic) · Redis · OpenStreetMap · Open-Meteo   │
└────────────────────────────────────────────────────────────────────────┘
```

- **Frontend**: React 18, TypeScript, Vite, custom editorial design system with fluid typography and full `prefers-reduced-motion` compliance.
- **Backend API**: Python 3.12 / 3.13, FastAPI, Pydantic v2, Uvicorn.
- **Persistence & Migrations**: PostgreSQL 15+, SQLAlchemy 2.0 (asyncio + asyncpg), Alembic.
- **Caching & Ephemeral State**: Redis 7+.
- **Information Providers**: OpenStreetMap (Overpass API + Nominatim geocoding) for spatial venue discovery.
- **Live Weather**: Open-Meteo API for real-time precipitation and adverse weather detection.

---

## Real-World Intelligence & Invariants

Dayform adheres to three strict engineering invariants:

1. **Grounded Venue Data**: Recommendations are backed by verified OpenStreetMap nodes. If a venue has no physical address or source URL, it is explicitly flagged.
2. **Honest Uncertainty**: Missing information is marked as `UNKNOWN`. Dayform never fabricates hours, reservations, or ticket prices.
3. **Graceful Degradation**: If an external provider is unreachable, Dayform falls back safely to cached fixtures without interrupting the user experience.

---

## Running Locally

### Prerequisites

- **Python**: 3.12 or 3.13
- **Node.js**: 18+ and `npm`
- **PostgreSQL**: 15+ (local or Docker)
- **Redis**: 7+ (local or Docker)

### 1. Database & Cache Services

```bash
docker compose up -d postgres redis
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e .

# Run database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

Backend will be online at `http://127.0.0.1:8000/` (Swagger docs at `/docs`).

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Open `http://localhost:5173/` in your browser.

---

## Testing & Quality

### Backend Test Suite
```bash
# Run all planning unit and domain tests
pytest backend/tests/unit/domain/planning backend/tests/unit/application/planning backend/tests/unit/infrastructure/planning -v

# Run integration tests
pytest backend/tests/integration/test_planning_api.py -v
```

### Frontend Code Quality
```bash
cd frontend

# Lint with Oxlint
npm run lint

# Typecheck and production build
npm run build
```

---

## Project Evolution

This repository reflects an iterative engineering journey across three distinct stages:

```text
CareerOS (M1–M7)              OpsOS (M8 Working Title)             DAYFORM (Canonical Product)
AI-powered job discovery   ──► Infrastructure orchestration   ──► Intelligent real-world planning
and application tailoring      and operational automation         "Give shape to your day"
```

1. **CareerOS (Milestones 1–7)**: Established clean architecture boundaries, async PostgreSQL migrations, JWT authentication, and AI provider abstractions.
2. **OpsOS (Milestone 8 Exploration)**: Explored deterministic decision engines, event monitoring, and human-in-the-loop action proposals.
3. **Dayform (Canonical Product)**: Synthesized these foundations into an intelligent real-world planning platform that turns human intent into real-world action.

*The GitHub repository identifier (`SimplyAlice/careeros`) and underlying PostgreSQL schemas are retained for historical and operational continuity.*

---

## License

This project is open-source under the [MIT License](LICENSE).
