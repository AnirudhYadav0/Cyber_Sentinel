# CyberSentinel — Security Operations Center (SOC) Platform

CyberSentinel is a full-stack Security Operations Center (SOC) monitoring and threat detection platform. It combines a Next.js (React, Tailwind CSS, Recharts) dashboard with a Python FastAPI backend and MongoDB Atlas persistence to ingest telemetry, evaluate detection rules, triage alerts, and manage incident response.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │    CyberSentinel Next.js Frontend       │
                      │  (SOC Command Center, Charts, Tables)   │
                      └────────────────────┬────────────────────┘
                                           │ HTTP / REST
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │        FastAPI Python Backend           │
                      │  ┌───────────────────────────────────┐  │
                      │  │  Telemetry Ingestion & Validation │  │
                      │  ├───────────────────────────────────┤  │
                      │  │  Rule-Based Threat Detection Engine│  │
                      │  ├───────────────────────────────────┤  │
                      │  │  Alert Triage & Incident Workflow │  │
                      │  └───────────────────────────────────┘  │
                      └────────────────────┬────────────────────┘
                                           │ PyMongo
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │          MongoDB Atlas / Local          │
                      │  - security_events    - alerts          │
                      │  - incidents          - audit_logs      │
                      │  - detection_rules    - detection_history
                      └─────────────────────────────────────────┘
```

---

## Threat Detection Engine (Phase 3)

The detection engine evaluates normalized security events against active detection rules within rolling time windows. It generates actionable alerts, deduplicates alerts across detection runs, and records detection run history.

### Configured Rules

| Rule ID | Rule Name | Severity | Default Threshold | Default Window | Applicable Event Types | Purpose |
|---|---|---|---|---|---|---|
| **AUTH-001** | Repeated Failed Logins | Critical | 5 attempts | 10 minutes | `auth.login_failed` | Detects brute-force authentication attempts or credential stuffing from a source IP or against an account. |
| **AUTH-002** | Repeated Unauthorized Access | High | 5 attempts | 10 minutes | `auth.access_denied` | Detects repeated 401/403 or permission-denied responses indicative of path traversal, fuzzing, or broken access control. |
| **TRAFFIC-001** | Unusual Request Volume | Medium | 30 requests | 5 minutes | `api.request` | Flags request rate anomalies that spike above baseline for investigation. |
| **PRIV-001** | Unexpected Privileged Action | High | 1 action | 30 minutes | `privilege.action` | Flags administrative actions falling outside the approved policy list (e.g., unauthorized role escalation, backup purge). |

### False-Positive Considerations & Limitations

- **AUTH-001**: Legitimate users may mistype passwords or have mobile devices retrying with stale cached tokens. Distributed attacks using diverse residential proxies may stay below single-IP thresholds.
- **AUTH-002**: Expired session tokens, broken frontend retry loops, or benign web crawlers can cause spikes in denied requests.
- **TRAFFIC-001**: Legitimate batch data exports, scheduled reporting jobs, or frontend polling can trigger request anomalies. Activity is flagged as suspicious for investigation, not an automatic DoS classification.
- **PRIV-001**: Break-glass emergency interventions or maintenance operations outside normal policy will trigger alerts. Requires accurate action categorization in metadata.

### Alert Deduplication

Each detection finding generates a deterministic deduplication key (`dedup_key`):
```
{rule_id}:{group_key}:{hourly_time_bucket}
# Example: AUTH-001:198.51.100.22:2026-10-25-11
```
When an alert with this key already exists in MongoDB, subsequent detection runs mark the finding as deduplicated without duplicating alerts or overwriting existing analyst notes or triage status (e.g. `Investigating`, `Resolved`).

---

## API Endpoints

### Threat Detection
- `POST /api/detection/run`: Executes on-demand detection scan (`{"lookback_minutes": 60}`).
- `GET /api/detection/rules`: Returns all configured detection rules and states.
- `PATCH /api/detection/rules/{rule_id}`: Updates threshold, window, severity, or enabled state.
- `GET /api/detection/history`: Returns paginated history of past detection runs.

### Security Telemetry & Log Ingestion
- `GET /api/events`: Paginated events with filtering by severity, outcome, event type, date, and search.
- `GET /api/events/{event_id}`: Single event lookup.
- `POST /api/events/ingest`: JSON event ingestion (single or bounded batch) with Pydantic validation and sanitization.
- `POST /api/events/upload`: Multipart file upload for `.json`, `.jsonl`, `.ndjson`, or `.log` files.

### Alerts & Incidents
- `GET /api/alerts`: List alerts with severity/status filtering and search.
- `PATCH /api/alerts/{alert_id}`: Triage alert (`Open` -> `Investigating` -> `Resolved`), analyst notes.
- `GET /api/incidents`: List incident cases.
- `POST /api/incidents`: Create incident case.
- `PATCH /api/incidents/{incident_id}`: Update incident status, notes, resolution.

### System Health
- `GET /api/health`: Service liveness check.
- `GET /api/ready`: Live MongoDB ping dependency readiness check (HTTP 200 ready, HTTP 503 degraded).

---

## Setup & Running Locally

### 1. Backend Setup
```bash
# Recommended Python version: Python 3.10+
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation will be available at: `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
# From repository root:
npm install
npm run dev
```
The Next.js dashboard will be available at: `http://localhost:3000`

---

## Running Automated Tests

Run the complete backend test suite (includes health checks, event ingestion, alert lifecycles, and detection engine tests using in-memory mocked MongoDB):
```bash
PYTHONPATH=backend ./backend/venv/bin/pytest backend/tests
```
All 29 tests execute with zero required external dependencies.
