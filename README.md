# OpsOS

**OpsOS — Intelligent Operations System**

An AI-powered operations platform designed to monitor systems, understand operational events, investigate incidents, recommend authorised actions, and eventually execute those actions through controlled tools.

OpsOS is being built incrementally and publicly, one engineering milestone at a time.

> **Observe → Understand → Investigate → Recommend → Approve → Execute → Verify → Audit**

The project originally began as **CareerOS**, a career-operations platform. The project has since been deliberately pivoted into OpsOS. The repository retains its historical `careeros` name for now, but the active product and architecture are OpsOS.

---

## What Is OpsOS?

OpsOS is an intelligent technical operations system.

It is designed around the idea of giving an operations engineer a system that can:

* receive operational events from services
* evaluate those events deterministically
* identify incidents
* investigate incidents using available system evidence
* recommend appropriate operational actions
* require approval before consequential actions
* execute only authorised actions through controlled interfaces
* verify the outcome
* maintain an auditable record of what happened

The long-term goal is not to build another dashboard or chatbot.

The goal is to build an operational system that can participate in the full incident-response loop while keeping humans in control of consequential actions.

---

## Core Operational Loop

```text
                    SYSTEMS
                       │
                       ▼
                     EVENTS
                       │
                       ▼
               EVENT EVALUATION
                       │
                       ▼
                   INCIDENT
                       │
                       ▼
                 INVESTIGATION
                       │
                       ▼
                 RECOMMENDATION
                       │
                       ▼
                    APPROVAL
                       │
                       ▼
                   EXECUTION
                       │
                       ▼
                   VERIFICATION
                       │
                       ▼
                     AUDIT
```

The system is being built from the bottom up.

Deterministic operational behaviour is implemented first. AI/LLM capabilities can be introduced later where they provide useful reasoning or interpretation without replacing the system's safety boundaries.

---

## Current Architecture

The current backend is organised around several layers:

```text
Events
  │
  ▼
Event Evaluation
  │
  ▼
Incidents
  │
  ▼
Investigation
  │
  ▼
Action Recommendation
  │
  ▼
Approval
  │
  ▼
Controlled Execution
  │
  ▼
Verification
  │
  ▼
Audit
```

The application is structured using domain entities, application services, repositories, infrastructure adapters, and API routes.

This separation allows operational decisions to be tested independently from infrastructure execution.

---

## Current Technology

* **Python**
* **FastAPI**
* **SQLAlchemy**
* **PostgreSQL**
* **Redis**
* **Docker / Docker Compose**
* **Alembic**
* **Pytest**
* **Ruff**
* **mypy**
* **GitHub Actions**

The system currently focuses primarily on the backend and operational domain. Additional infrastructure integrations will be introduced incrementally.

---

## Milestone Progress

OpsOS is being developed milestone-by-milestone in the open.

### Foundation

| Milestone                          | Status                          |
| ---------------------------------- | ------------------------------- |
| 0 — Foundations & architecture     | ✅ Complete                      |
| 1 — Core backend skeleton          | ✅ Complete                      |
| 2 — Database schema                | ✅ Complete                      |
| 3 — Job ingestion                  | ✅ Historical CareerOS milestone |
| 4 — Profile management             | ✅ Historical CareerOS milestone |
| 5 — AI scoring engine              | ✅ Historical CareerOS milestone |
| 6 — Resume/cover-letter generation | ✅ Historical CareerOS milestone |
| 7 — Authentication                 | ✅ Historical CareerOS milestone |

Milestones 3–7 belong to the original CareerOS product direction and are preserved as project history.

### OpsOS

| Milestone                                         | Status     |
| ------------------------------------------------- | ---------- |
| 8 — Operational backend foundation                | ✅ Complete |
| 9 — Event → Incident intelligence                 | ✅ Complete |
| 10 — Incident investigation                       | ✅ Complete |
| 11 — Deterministic action recommendation          | ✅ Complete |
| 12 — Approval-gated action execution              | 🚧 Next    |
| 13 — Verification and operational feedback        | 📋 Planned |
| 14 — Intelligent operations / controlled AI layer | 📋 Planned |

The roadmap may evolve as the system architecture develops.

---

## Milestone 8 — Operational Backend Foundation

The first major OpsOS milestone established the operational domain.

Implemented:

* Services
* Events
* Incidents
* Actions
* Approvals
* Audit logs
* Domain entities
* Repository layer
* Application services
* PostgreSQL persistence
* API routes
* Integration tests

This established the persistence and application foundation required for the operational loop.

---

## Milestone 9 — Event → Incident Intelligence

OpsOS can now evaluate incoming events and determine whether they represent an operational problem.

The initial evaluator is intentionally deterministic.

Examples of signals include:

* `CRITICAL` event severity
* `ERROR` event severity
* `ERROR` event type
* `ALERT` event type

Problematic events can create or associate with an active incident.

The system also records **why** the event was evaluated as problematic.

This reasoning is stored as structured operational evidence rather than being inferred later from an LLM.

---

## Milestone 10 — Incident Investigation

OpsOS can investigate an incident through:

```text
Incident
   │
   ├── Service
   │
   └── Events
```

The investigation endpoint collects the available evidence and produces deterministic findings.

The system does not pretend to know chronology when event timestamps are unavailable.

Instead, investigation responses explicitly report the ordering basis:

```json
{
  "ordering": {
    "basis": "event_id",
    "chronology_available": false
  }
}
```

This keeps operational reasoning grounded in observable evidence.

---

## Milestone 11 — Deterministic Action Recommendation

OpsOS can now move from:

```text
Incident → Investigation
```

to:

```text
Incident → Investigation → Recommendation
```

Recommendations are currently deterministic and based on structured evidence.

For example, a critical incident involving a degraded or unavailable service and a critical event can produce:

```json
{
  "action_type": "restart_service",
  "confidence": "deterministic",
  "requires_approval": true
}
```

Other supported recommendation paths include deployment rollback when structured deployment evidence is present and incident acknowledgement when an open/investigating incident contains an error or alert signal.

### Important safety boundary

Milestone 11 **does not execute actions**.

It does not:

* create an Action record
* create an Approval record
* restart infrastructure
* execute shell commands
* automatically approve anything
* use an LLM to make the decision

The recommendation layer is deliberately separated from execution.

---

## Milestone 12 — Approval-Gated Execution

The next milestone extends the operational loop:

```text
Recommendation
      │
      ▼
    Action
      │
      ▼
   Approval
      │
      ▼
  Authorised
  Execution
```

The intended safety model is:

1. OpsOS recommends an action.
2. An Action is created from the recommendation.
3. The action requires approval.
4. Only an approved action may execute.
5. Rejected actions cannot execute.
6. Execution happens through a controlled adapter/interface.
7. Arbitrary shell execution is not permitted.
8. Execution results will eventually feed into verification and audit.

The first execution implementation will use controlled, testable behaviour rather than destructive real-world infrastructure operations.

---

## Design Principles

### 1. Deterministic foundations first

Operational decisions should be reproducible and testable before introducing probabilistic reasoning.

### 2. Humans remain in control

Consequential actions require explicit authorisation.

### 3. Evidence over assumptions

The system should distinguish between what it knows, what it infers, and what it does not have enough evidence to determine.

### 4. No arbitrary execution

OpsOS should never turn an AI-generated instruction into an unrestricted shell command.

Actions are represented using controlled action types and execution interfaces.

### 5. Everything important should be auditable

The system is designed so that operational actions can eventually answer:

* What happened?
* What evidence was available?
* What did OpsOS recommend?
* Who approved it?
* What was executed?
* What happened afterwards?

### 6. AI is a component, not the architecture

OpsOS is not built around an LLM.

The operational system must remain useful and safe when AI reasoning is unavailable.

---

## Repository Structure

```text
backend/
├── app/
│   ├── domain/
│   │   └── entities/          # Operational domain entities
│   │
│   ├── application/
│   │   └── operations/        # Operational use cases
│   │
│   ├── infrastructure/
│   │   ├── db/                # Database models and repositories
│   │   └── ...
│   │
│   ├── api/
│   │   └── v1/                # FastAPI routes
│   │
│   ├── core/                  # Configuration and application infrastructure
│   └── main.py
│
├── alembic/                   # Database migrations
├── tests/
│   ├── unit/
│   └── integration/
│
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## Running OpsOS Locally

Clone the repository:

```bash
git clone https://github.com/SimplyAlice/careeros.git
cd careeros
```

Start the development environment:

```bash
docker compose up --build
```

The backend API is available at:

```text
http://localhost:8000/
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/api/v1/health
```

---

## Running Backend Tests

From the backend directory:

```bash
cd backend
pytest -v
```

Static analysis:

```bash
ruff check app tests
```

Type checking:

```bash
mypy app
```

Integration tests use PostgreSQL.

For local development, the Docker Compose PostgreSQL service can be exposed through:

```text
postgresql+asyncpg://careeros:<password>@localhost:5432/ca
```
