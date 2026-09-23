# Real Information Architecture & Providers — OpsOS Milestone 3

OpsOS is an intelligent planning platform that operates on the core promise:
> **"Tell me what you want to do. I'll figure out the rest."**

In Milestone 3, OpsOS transitioned from operating solely against a synthetic developer fixture catalog to planning against **authoritative, real-world information** grounded in actual places, activities, street addresses, opening hours, realistic pricing, and honest provenance.

---

## 1. Provider Evaluation & Selection

We audited five potential data providers to determine which information sources are realistic, legally compliant, affordable for development, and beneficial to the consumer planning experience:

| Provider | Real-World Coverage (Cape Town) | Pricing & Limits | Access Requirements | Licensing / Attribution | Decision & Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenStreetMap (OSM) / Overpass & Nominatim** | **Excellent** across all City Bowl, Waterfront, Camps Bay, Newlands, Bo-Kaap, and Table Mountain amenities, parks, cultural venues, and dining. | **$0** (Free community resource; rate limits <10,000 queries/day, <1 req/sec on Nominatim) | No secret API keys or credit cards required; requires respectful `User-Agent`. | Open Database License (ODbL); requires `© OpenStreetMap contributors` attribution. | **Selected as Primary Provider**. Open, reliable, zero risk of unexpected billing, rich in spatial tags, opening hours, and street addresses. |
| **City of Cape Town Open Data Portal (ArcGIS)** | **Authoritative for public spaces** (municipal parks, public nature reserves, heritage sites, scenic routes). | **$0** (Public open data services). | Public REST endpoints. | Open government data terms. | **Selected as Secondary / Complementary Source** for authoritative public parks, gardens, and nature reserves. |
| **Foursquare Places API** | Moderate commercial venues; weaker on public parks and natural sights. | 500 free calls/month hard cap, then $15 / 1,000 calls pay-as-you-go. | Mandatory developer account, API keys. | Commercial ToS; prohibits caching >30 days. | **Excluded for MVP**. 500 calls easily exhausted in automated CI/CD and developer tests, presenting high billing risks. |
| **Google Places API (New)** | Excellent commercial coverage. | Universal $200 credit retired in 2025/2026; per-SKU pay-as-you-go with mandatory credit card on GCP billing account. | Mandatory GCP billing account, credit card, restricted API keys. | Strict terms: no permanent caching; no multi-provider blending; mandatory map display. | **Excluded for open-source MVP**. Cannot commit API secrets or require credit card accounts for repository evaluation. |
| **Yelp Fusion API** | Near zero in South Africa. | Standard developer tier. | API key. | Commercial ToS. | **Excluded**. No viable South African footprint. |

---

## 2. Architecture & Normalisation

### Provider-Agnostic Abstraction
The application layer interacts exclusively with the abstract port:
`PlanningInformationProvider` (defined in `backend/app/application/planning/ports.py`).

No third-party HTTP requests, proprietary payloads, or provider-specific schemas leak into the domain.

```text
USER INTENTION
      ↓
UNDERSTANDING LAYER (PlanningUnderstandingPort)
      ↓
DECISION CRITERIA (DecisionCriteria)
      ↓
INFORMATION SERVICE (PlanningInformationService)
      ↓
INFORMATION PROVIDER (OpenStreetMapInformationProvider)
      ↓
NORMALISED DOMAIN ENTITIES (Place, Activity)
      ↓
DECISION ENGINE (decide, assess_location, assess_exclusions)
      ↓
PLAN ASSEMBLY & SELECTION (PlanSelectionService)
      ↓
CONSUMER EXPERIENCE ("Here's what I'd do")
```

### Normalised Domain Models
`Place` and `Activity` carry normalised, provider-neutral fields:
* `id`: Stable UUID
* `name`: Real name of the venue or activity
* `location`: General city/metro area (e.g. "Cape Town")
* `address`: Specific street address / neighborhood (e.g. "Rhodes Dr, Newlands, Cape Town", "30 Kloof St, Gardens")
* `category`: Normalised `InformationCategory` (`food`, `culture`, `nature`, `entertainment`, `shopping`, `wellness`)
* `price_from` / `cost`: Price in South African Rands (ZAR), or `None` if unlisted
* `opening_hours`: Verified operating hours (e.g. "Daily 08:00-18:00", "Tue-Sun 10:00-18:00")
* `minimum_group_size` / `maximum_group_size`: Physical capacity limits
* `source`: Data source identifier (e.g. `"openstreetmap"`, `"development_fixture"`)
* `freshness`: Provenance freshness state (`"live"`, `"recently_verified"`, `"cached"`, `"fixture"`)
* `verified_at`: Date or status of verification (e.g. `"2026-09"`, `"live"`)
* `source_url`: Official venue URL or map reference

---

## 3. Provenance & Freshness Hierarchy

To maintain complete honesty about real-world information without misleading users or pretending stale data is live, OpsOS enforces four distinct freshness states:

1. **`live`**: Information retrieved from the external provider during the active request.
2. **`cached`**: Information retrieved from the external provider earlier in the active process session.
3. **`recently_verified`**: A real-world record verified against an authoritative source (OSM node/way, official venue website, municipal registry) with documented provenance and verification date, but not queried via live network on this exact request.
4. **`fixture`**: Deterministic synthetic developer data used strictly for testing.

### Fallback Hierarchy
When an information search is performed:
```text
1. LIVE PROVIDER DATA (Nominatim / Overpass live query with 3s timeout)
         ↓ (if timeout, network error, or offline)
2. SESSION-CACHED REAL DATA
         ↓ (if cache miss)
3. VERIFIED REAL-WORLD CATALOG (authoritative real places & activities)
         ↓ (if criteria cannot be satisfied)
4. HONEST EMPTY RESULT ("I found no options matching your criteria")
```

**OpsOS NEVER silently falls back to synthetic fixtures when configured in real information mode.** Synthetic fixtures are only loaded when `settings.planning_provider == "fixture"` is explicitly set.

---

## 4. How Real Information Affects Planning

Real-world information materially influences the decision engine and plan assembly:

1. **Neighborhood & Spatial Matching**:
   * Evaluates specific sub-neighborhoods (`"Waterfront"`, `"Kloof Street"`, `"Camps Bay"`, `"Gardens"`, `"City Bowl"`, `"Newlands"`).
   * Matches both city-level and street-level location requests gracefully.
2. **Unlisted / Variable Pricing**:
   * Missing prices are treated as `None` rather than fabricated numbers.
   * Emits transparent, neutral budget explanations (`"Price not listed — menu or admission prices vary"`).
   * Does not disqualify viable options, while strictly enforcing ceilings when numeric prices are known.
3. **Capacity Constraints**:
   * Venues with known capacity limits (e.g. artisan roasteries max 6) are filtered out for large groups (e.g. group of 10), favoring expansive venues (e.g. Kirstenbosch Botanical Gardens max 15, Sea Point Promenade max 20).
4. **Negative Exclusions**:
   * `not_too_fancy`: Disqualifies fine-dining venues with tasting menus or formal requirements (e.g. `La Colombe` R890).
   * `no_outdoors`: Disqualifies nature reserves, open-air trails, and outdoor tours (e.g. `Lion's Head Trail`, `Sea Point Sunset Coastal Walk`).

---

## 5. Consumer UI Presentation

The frontend preserves the clean consumer feel without leaking internal developer jargon or raw database IDs:
* **Freshness Badge**: Displays `✓ Verified real-world places` or `● Live information`.
* **Real Addresses**: Renders neighborhood/street context on each stop (e.g. `Rhodes Dr, Newlands`, `30 Kloof St, Gardens`).
* **Opening Hours**: Displays `🕐 Daily 08:00–18:00` directly on the timeline step when known.
* **Pricing Transparency**: Formats unlisted prices as `"Price not listed"` and zero-cost amenities as `"Free"`.
* **Attribution**: Respects ODbL by displaying `Map and place information © OpenStreetMap contributors`.

---

## 6. Environment Configuration

In `.env` or application configuration:
```bash
# Provider selection: "openstreetmap" (default) or "fixture" (tests)
PLANNING_PROVIDER=openstreetmap

# Timeout for live OSM geocoding requests (seconds)
OPENSTREETMAP_TIMEOUT_SECONDS=3.0
```

---

## 7. Deferred Items (Out of Scope for Milestone 3)

The following features remain deliberately deferred:
* Live booking & table reservations
* In-app payments & ticketing
* Live turn-by-turn navigation & routing
* Real-time GPS user tracking
* Calendar integrations
