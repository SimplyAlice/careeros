# OpsOS

> **Intelligent real-world planning.**  
> *“Tell me what you want to do. I’ll figure out the rest.”*

OpsOS is an intelligent planning platform that turns a plain-spoken human intention into an actionable, coherent, budget-aware, and time-aware real-world plan.

---

## The Problem

Planning a real outing is broken and fragmented. Today, putting together a simple day out forces you to juggle dozens of browser tabs and apps:

- **Search engines** return thousands of disconnected blog posts and sponsored listicles.
- **Maps** show pins without understanding your budget, group pacing, or schedule constraints.
- **Venue websites** bury opening hours, dress codes, and pricing behind clunky interfaces.
- **Messaging apps and spreadsheets** become messy scratchpads for calculating travel buffers and total spend.

A collection of bookmarks or pins is not a plan. Real plans require understanding who is going, how much money can be spent, what times venues actually operate, how far apart they are, and what happens when someone runs 45 minutes late.

OpsOS brings that reasoning into a unified, deterministic planning engine.

---

## Core Loop

OpsOS operates through an explicit six-stage loop:

```text
INTENTION ──► UNDERSTAND ──► RESEARCH ──► PLAN ──► ADAPT ──► EXECUTE
   │               │             │          │        │          │
   │               │             │          │        │          └─► Directions, calls, web links, progress
   │               │             │          │        └─► Conversational tweaks ("running 45m late")
   │               │             │          └─► Logical timeline, transit buffers, budget headroom
   │               │             └─► Real places, opening hours, pricing (OpenStreetMap, Overpass)
   │               └─► Structured context (people, budget ceiling, temporal window, exclusions)
   └─► Natural human thought ("something fun Saturday with 4 friends under R500")
```

---

## Capabilities

- **Natural-Language Understanding**: Parses natural speech into structured context (party size, temporal windows, budget ceilings, occasion types, and negative constraints) without rigid forms.
- **Contextual Constraint Extraction**: Distinguishes hard requirements (e.g. *"no outdoors"*, *"under R500"*, *"home by 6pm"*) from soft aesthetic preferences (*"romantic"*, *"casual"*).
- **Real-World Place Discovery**: Grounded in verified places with real street addresses, categories, and operating hours via OpenStreetMap and Nominatim.
- **Temporal Sequencing & Pacing**: Calculates start and end times for each stop with realistic dwell times and geographic travel buffers.
- **Budget Tracking & Invariants**: Computes transparent per-person and group totals, tracks remaining headroom, and flags budget overages deterministically.
- **Candidate Customization**: Browse categorized alternatives for any stop with instant cost trade-off notes before confirming.
- **Adaptive Replanning**: Conversational modification requests (*"Make it cheaper"*, *"We're running 45 minutes late"*) recalculate the schedule with a minimal, non-destructive diff preserving unaffected stops.
- **Real-World Execution Layer**: Provides one-tap directions in Google Maps, direct telephone links, venue websites, and completed-stop tracking.
- **Live Intelligence & Monitoring**: Evaluates active plans against real-time signals (hourly precipitation via Open-Meteo and venue closing times) without silent mutations.

---

## Technical Architecture

OpsOS is structured around clean architecture principles with strict boundary separation:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React / Vite)                       │
│     Cinematic Scrollytelling · Workspace · Timeline · Adaptation Diff  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Application Layer                        │
│            Endpoints: /auth · /planning/requests · /adapt · /actions   │
└──────────────────┬──────────────────────────────────┬──────────────────┘
                   │                                  │
┌──────────────────▼──────────────────┐   ┌───────────▼──────────────────┐
│        Application Services         │   │      Domain Planning Engine  │
│  Planning · Adaptation · Execution  │   │  Understanding · Decisions   │
│       Live Intelligence Service     │   │  Temporal Logic · Invariants │
└──────────────────┬──────────────────┘   └───────────┬──────────────────┘
                   │                                  │
┌──────────────────▼──────────────────────────────────▼──────────────────┐
│                    Infrastructure & Providers                          │
│   PostgreSQL (Asyncpg / Alembic) · Redis · OpenStreetMap · Open-Meteo   │
└────────────────────────────────────────────────────────────────────────┘
```

- **Frontend**: React 18, TypeScript, Vite, custom responsive design system with fluid typography and full `prefers-reduced-motion` compliance.
- **Backend API**: Python 3.13, FastAPI, Pydantic v2, Uvicorn.
- **Persistence & Migrations**: PostgreSQL, SQLAlchemy 2.0 (asyncio + asyncpg), Alembic migrations.
- **Caching & Ephemeral State**: Redis.
- **Information Providers**: OpenStreetMap (Overpass API + Nominatim geocoding) for spatial venue discovery.
- **Live Weather**: Open-Meteo API for real-time precipitation and adverse weather detection.

---

## Product Principles

1. **Natural Language First**: Users should never have to navigate a maze of filter menus to communicate what they want.
2. **Constraints Matter**: Negative constraints (*"not too fancy"*, *"no outdoors"*) are strictly enforced, not treated as suggestions.
3. **Plans, Not Lists**: A list of places is not an itinerary. Plans require sequence, timing, travel buffers, and budget coherence.
4. **Explain Decisions**: Every recommendation includes plain-language human rationale, never exposing raw machine scores or internal IDs.
5. **Honest Uncertainty**: Missing data is marked as `UNKNOWN`, never assumed. If a live provider is unreachable, the system fails safely without breaking existing plans.
6. **User Remains in Control**: Dynamic adaptations produce reviewable diffs. Changes are never applied behind the user's back.
7. **Real-World Execution**: A plan ends in the real world with directions, direct phone calls, and schedule tracking.

---

## Local Setup

### Prerequisites

- **Python**: 3.12 or 3.13
- **Node.js**: 18+ and `npm`
- **PostgreSQL**: 15+ (local instance or Docker)
- **Redis**: 7+ (local instance or Docker)

### 1. Database & Cache Services

Using Docker:

```bash
docker compose up -d postgres redis
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e .

# Configure environment variables
# Copy .env.example to .env and adjust credentials if needed
cp ../.env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

Backend endpoints will be available at `http://127.0.0.1:8000/`.

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run linter
npm run lint

# Build for production
npm run build
```

Frontend application will be accessible at `http://localhost:5173/`.

---

## Demo Flow

The fastest way to experience OpsOS:

1. **Enter an Intention**: On the homepage, enter:
   > *“I want to do something fun this Saturday with 4 friends in Cape Town under R500.”*
2. **Review Understanding**: OpsOS extracts 5 people total (user + 4 friends), Saturday timing, Cape Town location, and an R500 strict ceiling.
3. **Inspect Proposed Itinerary**: OpsOS sequences eligible local venues with verified hours, travel times, and an R80 buffer.
4. **Swap a Stop**: Click **"Swap stop"** on any venue to preview categorized alternatives with clear cost trade-offs.
5. **Save the Itinerary**: Click **"Save Itinerary"** to persist the plan and transition to the execution view.
6. **Test Adaptive Recalibration**:
   - In the follow-up tweak box, enter: *“Actually, we’re running 45 minutes late.”*
   - OpsOS shifts downstream start times, verifies venue closing buffers, and displays a review diff.
7. **Execute in the Real World**: Click **"Google Maps"** to open directions, or check off a stop to update the active schedule.
8. **Check Live Intelligence**: Click **"Check Live"** to verify current operating hours and weather conditions.

---

## Current Status & Boundaries

OpsOS is a **completed release candidate and portfolio project**.

- **Provider Coverage**: Real-world data is currently grounded in Cape Town, South Africa via OpenStreetMap and Open-Meteo.
- **Provider Accuracy**: Venue operating hours and price levels are derived from open community data and heuristics.
- **Bookings**: OpsOS provides direct links and phone dialing rather than automated booking transactions.
- **Deployment**: Configured for local development and containerized evaluation.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
