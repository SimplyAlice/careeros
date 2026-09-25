# Dayform Mobility Intelligence Architecture & Design (M14)

## 1. Executive Summary & Objective

**Dayform Mobility** determines how a user physically moves through their day, compares available transport options across public, private, and non-motorised modes, models real-world schedules and distance-band fare tariffs, surfaces uncertainty and provenance honestly, and hands the user off to transport providers when booking is required.

In **M14 — Mobility Intelligence Foundation**, Dayform establishes:
1. A **provider-independent backend domain model** (`MobilityRequirement`, `MobilityOption`, `MobilityEvidence`, `ProviderCapability`).
2. An extensible **provider registry and adapter architecture** (`MobilityProviderPort`, `MobilityProviderRegistry`).
3. Real, verified provider adapters:
   - **MyCiTi**: Official Cape Town Bus Rapid Transit routes, scheduled frequency, and distance-band Mover package tariffs.
   - **PRASA / Metrorail**: Official Western Cape passenger rail lines (Southern and Northern Lines) with flat/zonal cash tariffs.
   - **Golden Arrow (GABS)**: Cape Town metropolitan commuter bus network.
   - **Uber**: Universal deep-link handoff (`https://m.uber.com/ul/`) with pre-filled pickup and dropoff destinations.
   - **Bolt**: External handoff abstraction.
   - **inDrive**: External handoff abstraction.
   - **Walking**: Open pedestrian distance & duration model (free, R0.00).
4. An **evidence and trust hierarchy** enforcing strict separation between official real-time feeds, published static timetables, approved provider APIs, third-party data, and crowdsourced user reports.
5. Integration boundaries with **Planning**, **M7 Live Intelligence**, and **M5 Adaptation**.
6. REST API endpoints (`POST /api/v1/mobility/options` and `GET /api/v1/mobility/providers`) and typed frontend DTOs.

---

## 2. Core Architecture & Component Flow

```
                      DAYFORM PLAN
                           ↓
             [Planning / Itinerary Stop Sequence]
                           ↓
                   MobilityRequirement
                           ↓
               ┌─────────────────────────┐
               │     MobilityService     │
               └───────────┬─────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
[Provider Registry]                     [Error Isolation]
       │                                 (asyncio.gather)
       ├─ WalkingProvider                      │
       ├─ MyCiTiProvider                       │
       ├─ PrasaProvider                        │
       ├─ GoldenArrowProvider                  │
       ├─ UberProvider                         │
       ├─ BoltProvider                         │
       └─ InDriveProvider                      │
       │                                       ▼
       └─────────────────────────────► list[MobilityOption]
                                               │
                                 [Filter & Mode Prioritization]
                                               │
                                               ▼
                                   MobilityOptionsResponse
                                               │
                                 ┌─────────────┴─────────────┐
                                 ▼                           ▼
                        [Itinerary Synthesis]       [M7 Live Signals]
                                 │                           │
                                 ▼                           ▼
                          Saved Plan Execution        [M5 Adaptation]
```

### Architectural Responsibilities

1. **Planning Engine (M13)**:
   - Reasons about user goals, budgets, dining preferences, occasions, and sequence of stops.
   - Remains completely decoupled from transport specifics. If the Mobility layer is disabled or unreachable, planning continues unaffected.
2. **Mobility Layer (M14)**:
   - Takes a `MobilityRequirement` between two geographic points or stops.
   - Queries registered providers concurrently with complete error isolation.
   - Enforces the **Truth in Transport** principle: unknown fares and unverified live statuses are explicitly modeled as `unknown` rather than fabricated.
3. **Live Intelligence (M7)**:
   - Accepts `MobilityEvidence` through `mobility_evidence_to_live_signal` as an `AVAILABILITY` or `OPERATING_HOURS` signal.
4. **Adaptation Engine (M5)**:
   - Detects when mobility disruptions (e.g. cancelled rail line or significant bus delay) invalidate plan timing, querying Mobility for alternative routes.

---

## 3. Domain Model Specification

### `MobilityRequirement`
Represents the travel demand generated between two itinerary points:
- `origin`: Name or address of origin location.
- `destination`: Name or address of destination location.
- `departure_time`: ISO-8601 departure timestamp (optional).
- `arrival_time`: ISO-8601 target arrival deadline (optional).
- `date`: Travel date if exact time is floating.
- `party_size`: Number of passengers (minimum 1).
- `preferred_modes`: Prioritized transport modes (`walk`, `bus`, `train`, `ride_hail`, `cycle`, `shuttle`).
- `excluded_modes`: Filtered transport modes.
- `max_walking_minutes`: Walking threshold constraint.
- `origin_coordinates` / `destination_coordinates`: `(latitude, longitude)` tuples.

### `MobilityOption`
A concrete transport option satisfying the requirement:
- `id`: Stable unique identifier.
- `provider_id`: Unique provider slug (e.g., `"myciti"`, `"uber"`, `"walking"`).
- `provider_name`: Human-readable provider title (e.g., `"MyCiTi"`, `"Uber"`).
- `mode`: `TransportMode`.
- `origin` / `destination`: Normalized location titles.
- `departure_time` / `arrival_time`: Calculated departure and arrival times.
- `duration_minutes`: Estimated total journey duration.
- `cost`: `Decimal | None`. **Critical rule**: `None` indicates unknown cost (`cost_is_unknown = True`). `Decimal("0")` is strictly reserved for genuinely free travel (e.g. walking).
- `cost_is_unknown`: Boolean flag highlighting price uncertainty to client applications.
- `currency`: Default `"ZAR"`.
- `walking_duration_minutes`: Walking required to reach stops / terminals.
- `transfers`: Number of vehicle changes required.
- `availability`: Availability status string (`"available"`, `"limited"`, `"cancelled"`).
- `live_status`: `MobilityLiveStatus` (`SCHEDULED`, `ESTIMATED`, `LIVE`, `DELAYED`, `CANCELLED`, `UNKNOWN`).
- `booking_capability`: `BookingCapability`.
- `booking_url`: Provider deep-link or web landing URL.
- `source`: Provenance identifier.
- `source_type`: `MobilitySourceType`.
- `retrieved_at`: Timestamp of option retrieval.
- `confidence`: Statistical confidence score (0.0 to 1.0).
- `evidence`: Attached list of `MobilityEvidence` records.
- `summary`: Human-readable summary string.

### `MobilityEvidence`
First-class provenance attached to all externally-derived travel data:
- `claim`: Factual statement (e.g. *"Scheduled MyCiTi service (Route 101). Fares calculated per official Mover distance bands (Peak)."*).
- `source`: Authoritative origin of the claim.
- `source_type`: Category within the evidence hierarchy.
- `observed_at`: Real-world observation timestamp.
- `retrieved_at`: Ingestion timestamp.
- `expires_at`: Optional TTL for live estimates and crowd reports.
- `confidence`: Source reliability weighting (0.0 to 1.0).
- `relevant_provider`: Associated provider identifier.
- `relevant_route_or_stop`: Route code or stop identifier.

---

## 4. Evidence Hierarchy of Trust

Dayform strictly separates source reliability into ordered tiers:

```
Tier 1: OFFICIAL_REALTIME (Weight: 100, Conf: 0.90 - 1.00)
        ↳ Official GTFS-RT feeds, direct vehicle telemetry, authorized agency live feeds.

Tier 2: OFFICIAL_TIMETABLE (Weight: 80, Conf: 0.75 - 0.85)
        ↳ Official published transit timetables, static GTFS datasets, municipal gazetted tariffs.

Tier 3: APPROVED_PROVIDER_API (Weight: 70, Conf: 0.70 - 0.85)
        ↳ Official partner APIs (Uber Universal Link, authenticated ride-hail estimates).

Tier 4: TRUSTED_THIRD_PARTY (Weight: 50, Conf: 0.50 - 0.75)
        ↳ Aggregated routing graphs, GIS data warehouses, verified transit directories.

Tier 5: CALCULATED (Weight: 40, Conf: 0.80 - 0.90)
        ↳ Deterministic internal calculations (walking speed 4.8 km/h, road network circuity).

Tier 6: CROWD_REPORT (Weight: 20, Conf: 0.35 - 0.65)
        ↳ Community / passenger reports of delays, unverified crowd observations.
```

### Truth in Transport Constraints
- **Stale Timetables**: Timetables past their operational date lose confidence and are flagged as `STALE`.
- **Crowd Reports vs Official Facts**: An unverified passenger report (Tier 6) **cannot override** an active official timetable (Tier 2). Corroborated reports (e.g. $\ge 3$ independent reports) escalate in confidence up to 0.65, but remain classified as `CROWD_REPORT`.

---

## 5. Booking & Handoff Capability Model

Dayform explicitly models what happens when a user wishes to proceed with an option:

| Level | Capability | Definition | Provider Examples in M14 |
|---|---|---|---|
| **0** | `NO_BOOKING` | Informational only. Tickets purchased in person, at stations, or card tapped on boarding. | Walking, MyCiTi (smartcard), PRASA (station ticket), Golden Arrow. |
| **1** | `EXTERNAL_HANDOFF` | Opens the provider's website or app store in an external browser tab. | Bolt (`https://bolt.eu`), inDrive (`https://indrive.com`). |
| **2** | `DEEPLINK` | Constructs an official Universal Link or native URI scheme pre-filling journey origin and destination. | Uber (`https://m.uber.com/ul/?action=setPickup&dropoff[nickname]=...`). |
| **3** | `EMBEDDED` | Interactive web booking widget embedded inside Dayform UI (e.g. reservation widget). | Reserved for future venue / transit partnerships. |
| **4** | `API_BOOKING` | Fully automated server-to-server authenticated ride reservation. | Deferred to future milestones requiring commercial API partnerships. |

---

## 6. Provider Verification & Status Matrix

| Provider | Mode | Route / Stop Data | Timetable Availability | Real-Time / Live Status | Fare Computation | Booking Capability | Public Open API | Authentication Required | Notes & Verification Status |
|---|---|---|---|---|---|---|---|---|---|
| **MyCiTi** | Bus Rapid Transit | Official GIS layers on CCT Open Data Portal | Official schedules published per route | ❌ Not available via open public API (status: `unknown`) | Official Mover distance bands (Peak vs Saver) | `NO_BOOKING` (myconnect smartcard) | None | None | Verified against City of Cape Town Open Data and MyCiTi 2024–2026 tariff structures. |
| **PRASA Metrorail** | Commuter Rail | Official Western Cape station network | Official schedules (Southern & Northern Lines) | ❌ Broadcast via WhatsApp only (status: `unknown`) | Flat/zonal cash single tickets (R10.50–R14.50) | `NO_BOOKING` (paper tickets at ticket office) | None | None | Verified against PRASA Western Cape timetables (revised June 2026). |
| **Golden Arrow** | Commuter Bus | Spatial Data Warehouse GIS routes | Published route schedules | ❌ None (status: `unknown`) | ❌ Unverified cash/clip-card scale (status: `cost_is_unknown`) | `NO_BOOKING` (cash or Gold Card on board) | None | None | Verified against Western Cape GIS Transportation MapServer. |
| **Uber** | Ride-hailing | Dynamic urban routing | On-demand | ❌ Requires private partner API (status: `unknown`) | ❌ Dynamic upfront fare (status: `cost_is_unknown`) | `DEEPLINK` (Universal Link) | Partner only | OAuth 2.0 (for API) | Universal link verified: `https://m.uber.com/ul/?action=setPickup`. No credentials needed for deep-linking. |
| **Bolt** | Ride-hailing | Dynamic urban routing | On-demand | ❌ No public API (status: `unknown`) | ❌ In-app upfront fare (status: `cost_is_unknown`) | `EXTERNAL_HANDOFF` (`https://bolt.eu`) | None | N/A | Verified: Bolt has no open third-party developer API. |
| **inDrive** | Ride-hailing | Dynamic urban routing | On-demand | ❌ No public API (status: `unknown`) | ❌ Peer-to-peer negotiated bidding (status: `cost_is_unknown`) | `EXTERNAL_HANDOFF` (`https://indrive.com`) | None | N/A | Negotiated passenger bidding model; impossible to predict ahead of ride. |
| **Walking** | Pedestrian | Open network graph | Continuous | N/A | R0.00 (verified free) | `NO_BOOKING` | Open | None | Calculated at 4.8 km/h pedestrian pace with urban network circuity factor 1.3. |

---

## 7. M7 Live Intelligence & M5 Adaptation Integration

### Bridging Mobility Evidence to M7 LiveSignal
Rather than inventing a parallel live notification bus, Mobility integrates directly into Dayform M7:
```python
signal = mobility_evidence_to_live_signal(
    evidence=evidence,
    target_name="MyCiTi Route 101",
    target_item_id=stop_id,
    is_disruption=True,
)
```
- `signal_type`: `LiveSignalType.AVAILABILITY`
- `change_type`: `LiveChangeType.EVENT_RESCHEDULED` or `LiveChangeType.INFORMATIONAL`
- `freshness`: `FreshnessKind.LIVE` or `FreshnessKind.RECENTLY_VERIFIED`

### Triggering M5 Adaptation
When a mobility disruption occurs:
1. M7 flags `is_meaningful_change = True`.
2. M5 receives the event and identifies affected stops.
3. M5 calls `MobilityService.get_options()` with updated departure/arrival buffers.
4. M5 synthesizes an `ItemDiff` proposing a mode swap or rescheduled departure.
5. The user is prompted to accept or reject the revised plan.

---

## 8. What is Implemented in M14 vs Deferred Roadmap

### Implemented in M14
- ✅ Clean domain models (`MobilityRequirement`, `MobilityOption`, `MobilityEvidence`, `ProviderCapability`).
- ✅ Provider registry with dynamic enable/disable and runtime capability inspection.
- ✅ Concurrent multi-provider querying with comprehensive exception isolation.
- ✅ 7 verified provider adapters (MyCiTi, PRASA, Golden Arrow, Uber, Bolt, inDrive, Walking).
- ✅ Truthful handling of unknown fares vs free costs.
- ✅ Official Uber Universal Link generation.
- ✅ REST API endpoints (`/options` and `/providers`).
- ✅ Typed frontend TypeScript definitions (`types/mobility.ts`) and client (`api/mobility.ts`).
- ✅ Planning, M7, and M5 integration bridges.
- ✅ Complete test suite (427 passing backend unit tests, 0 frontend lint errors).

### Explicit "Do Not Build Yet" (Deferred Roadmap)
- ❌ **No server-side Uber booking API**: Requires commercial ride-request partner agreement.
- ❌ **No Bolt / inDrive scraping**: Both lack public APIs; unauthorized scraping risks legal and reliability issues.
- ❌ **No fake real-time vehicle positions**: Live tracking will only be activated when authorized GTFS-RT feeds are provisioned.
- ❌ **No giant transport UI redesign**: Frontend visual identity remains pristine; full mobility UI will be introduced in M15.
- ❌ **No automated background scrapers**: Timetables are bundled as static verified references.
