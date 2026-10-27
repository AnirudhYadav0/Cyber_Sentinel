# CyberSentinel — Security Operations Center (SOC) Platform

CyberSentinel is a full-stack Security Operations Center (SOC) monitoring and threat detection platform. It combines a Next.js (React, Tailwind CSS, Recharts) dashboard with a Python FastAPI backend and MongoDB Atlas persistence to ingest telemetry, evaluate detection rules, triage alerts, and manage incident response.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │    CyberSentinel Next.js Frontend       │
                      │  (SOC Command Center, Charts, Tables)   │
                      └────────────────────┬────────────────────┘
                                           │ HTTP / REST (JWT Bearer Auth)
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │        FastAPI Python Backend           │
                      │  ┌───────────────────────────────────┐  │
                      │  │  Authentication & RBAC (JWT/Bcrypt)│  │
                      │  ├───────────────────────────────────┤  │
                      │  │  Rate Limiting & Security Headers │  │
                      │  ├───────────────────────────────────┤  │
                      │  │  Telemetry Ingestion & Validation │  │
                      │  ├───────────────────────────────────┤  │
                      │  │  Rule-Based Threat Detection Engine│  │
                      │  ├───────────────────────────────────┤  │
                      │  │  Alert Triage & Incident Workflow │  │
                      │  └───────────────────────────────────┘  │
                      └────────────────────┬────────────────────┘
                                           │ PyMongo (Least-Privilege TLS)
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │          MongoDB Atlas / Local          │
                      │  - security_events    - alerts          │
                      │  - incidents          - audit_logs      │
                      │  - users              - detection_rules │
                      │  - detection_history                    │
                      └─────────────────────────────────────────┘
```

---

## Security Architecture & Hardening (Phase 5)

CyberSentinel implements defense-in-depth application security controls:

### 1. Authentication & Role-Based Access Control (RBAC)
- **Password Hashing**: Passwords are cryptographically salted and hashed using `bcrypt` (work factor 12). Plaintext passwords are never logged, stored, or returned in API responses.
- **Access Tokens**: Ephemeral JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`). Tokens include expiration (`exp`), issue time (`iat`), and subject claims (`sub`).
- **Role Enforcement**:
  - `admin`: Full administrative control, including tuning threat detection rules (`PATCH /api/detection/rules/{id}`), provisioning users (`POST /api/auth/register`), and triage actions.
  - `analyst`: Investigates alerts, updates triage status, triggers detection scans, logs incident cases, and ingests telemetry.
- **Audit Logging**: Sensitive administrative actions and authentication failures are recorded in the `audit_logs` collection with timestamps, actor IDs, and IP addresses.

### 2. Rate Limiting & DoS Protection
- **Sliding-Window Limiter**: Protects sensitive endpoints with configurable request thresholds:
  - `/api/auth/login`: 15 requests / minute (prevents credential stuffing and brute-force).
  - `/api/events/ingest`: 120 requests / minute.
  - `/api/events/upload`: 30 uploads / minute.
  - `/api/detection/run`: 30 scans / minute.
- Returns standard HTTP `429 Too Many Requests` with `Retry-After` headers.

### 3. Payload & File Upload Protection
- **Global Body Limit**: Enforces a 15MB request body size cap (`Content-Length`) to prevent memory exhaustion.
- **Chunked File Streaming**: File uploads on `/api/events/upload` are processed in 64KB streamed chunks up to a 10MB threshold. Oversized files are rejected with HTTP `413 Content Too Large` before buffering into RAM.
- **MIME & Extension Whitelist**: Only `.json`, `.jsonl`, `.ndjson`, and `.log` files with valid UTF-8 character encoding are accepted.

### 4. Defense-in-Depth HTTP Headers
Every API response includes industry-standard security headers:
- `X-Content-Type-Options: nosniff` (MIME sniffing prevention)
- `X-Frame-Options: DENY` (Clickjacking mitigation)
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`
- `X-Request-ID`: Distributed trace identifier for correlation in observability pipelines.

---

## Threat Detection Engine (Phase 3)

The detection engine evaluates normalized security events against active detection rules within rolling time windows.

### Configured Rules

| Rule ID | Rule Name | Severity | Default Threshold | Default Window | Applicable Event Types | Purpose |
|---|---|---|---|---|---|---|
| **AUTH-001** | Repeated Failed Logins | Critical | 5 attempts | 10 minutes | `auth.login_failed` | Detects brute-force authentication attempts or credential stuffing from a source IP or against an account. |
| **AUTH-002** | Repeated Unauthorized Access | High | 5 attempts | 10 minutes | `auth.access_denied` | Detects repeated 401/403 or permission-denied responses indicative of path traversal, fuzzing, or broken access control. |
| **TRAFFIC-001** | Unusual Request Volume | Medium | 30 requests | 5 minutes | `api.request` | Flags request rate anomalies that spike above baseline for investigation. |
| **PRIV-001** | Unexpected Privileged Action | High | 1 action | 30 minutes | `privilege.action` | Flags administrative actions falling outside the approved policy list (e.g., unauthorized role escalation, backup purge). |

### Alert Deduplication
Deterministic deduplication key format:
```
{rule_id}:{group_key}:{hourly_time_bucket}
# Example: AUTH-001:198.51.100.22:2026-10-25-11
```
Deduplication preserves existing analyst triage status (`Investigating`, `Resolved`) and notes without creating duplicate alerts.

---

## API Endpoints Reference

### Authentication (`/api/auth`)
- `POST /api/auth/login`: Authenticate analyst/admin and receive JWT Bearer token (Rate-limited).
- `GET /api/auth/me`: Retrieve current authenticated profile and permissions.
- `POST /api/auth/register`: Provision new analyst user (Admin-only).
- `POST /api/auth/logout`: Terminate session.

### Threat Detection (`/api/detection`)
- `POST /api/detection/run`: Executes on-demand detection scan (Analyst/Admin).
- `GET /api/detection/rules`: Returns all configured detection rules and states.
- `PATCH /api/detection/rules/{rule_id}`: Tune detection rule (Admin-only).
- `GET /api/detection/history`: Paginated detection run history.

### Security Telemetry (`/api/events`)
- `GET /api/events`: Paginated events with filtering by severity, outcome, event type, date, and search.
- `GET /api/events/{event_id}`: Single event lookup.
- `POST /api/events/ingest`: JSON event ingestion with schema sanitization.
- `POST /api/events/upload`: Chunked file upload for telemetry logs (.json, .jsonl, .log).

### Alerts & Incidents
- `GET /api/alerts`: List alerts with severity/status filtering.
- `PATCH /api/alerts/{alert_id}`: Triage alert (`Open` -> `Investigating` -> `Resolved`), analyst notes.
- `GET /api/incidents`: List incident cases.
- `POST /api/incidents`: Create incident case (Analyst/Admin).
- `PATCH /api/incidents/{incident_id}`: Update incident status, notes, resolution.

### System Health
- `GET /api/health`: Service liveness check.
- `GET /healthz`: Container orchestrator probe.
- `GET /api/ready`: Live MongoDB ping dependency readiness check (HTTP 200 ready, HTTP 503 degraded).

---

## Deployment Guide

### 1. Database Configuration (MongoDB Atlas)
1. **Network Access**: Add your backend hosting IP or range to the IP Access List (avoid `0.0.0.0/0` in production if static IPs or VPC peering are available).
2. **Database User**: Create a least-privilege user with `readWrite` permission scoped exclusively to the `cybersentinel` database:
   - Built-in Role: `readWrite@cybersentinel` (Do NOT grant `atlasAdmin` or cluster-wide roles).
3. **Connection String**: Obtain standard SRV URI:
   ```
   mongodb+srv://<soc_user>:<soc_password>@cluster0.abcde.mongodb.net/cybersentinel?retryWrites=true&w=majority
   ```

### 2. Backend Deployment (Render / Docker)
- **Deployment via Render**: Use the included `render.yaml` blueprint:
  1. Link the repository to Render.
  2. Configure environment variables:
     - `MONGODB_URI`: Atlas connection string
     - `CORS_ORIGINS`: Your Vercel frontend domain (`https://cybersentinel.vercel.app`)
     - `JWT_SECRET_KEY`: Auto-generated 32-character random key
     - `APP_ENV`: `production`
  3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  4. Health check endpoint: `/healthz`
- **Deployment via Docker**:
  ```bash
  docker build -t cybersentinel-backend -f backend/Dockerfile backend/
  docker run -p 8000:8000 --env-file backend/.env cybersentinel-backend
  ```

### 3. Frontend Deployment (Vercel)
1. Import repository into Vercel.
2. Build Settings: Next.js (Preset), Build Command: `next build`.
3. Configure Environment Variable:
   - `NEXT_PUBLIC_API_BASE_URL`: `https://your-api.onrender.com`
4. Deploy using included `vercel.json`.

---

## Deployment Smoke Test Checklist

Post-deployment verification steps to confirm end-to-end integrity:

- [ ] **Frontend Accessibility**: Next.js dashboard loads without errors at the production domain.
- [ ] **Backend Health Probe**: `GET /healthz` returns `{"status":"ok"}`.
- [ ] **Database Readiness**: `GET /api/ready` returns HTTP 200 with `{"database":"connected"}`.
- [ ] **Authentication Flow**:
  - `POST /api/auth/login` issues a signed JWT access token for admin/analyst.
  - Invalid credentials return HTTP 401.
  - `GET /api/auth/me` validates the token and returns the current user profile.
- [ ] **Role Authorization**:
  - Analyst token modifying `/api/detection/rules/{id}` returns HTTP 403 Forbidden.
  - Admin token succeeds.
- [ ] **Rate Limiting**: Exceeding 15 rapid login attempts returns HTTP 429 with `Retry-After`.
- [ ] **Telemetry Ingestion**: `POST /api/events/ingest` creates event and increments counter.
- [ ] **Detection Engine**: `POST /api/detection/run` triggers scan and evaluates active rules.
- [ ] **Alert Triage**: `PATCH /api/alerts/{id}` updates triage status and records audit log.
- [ ] **CORS Verification**: Browser console shows zero CORS preflight errors from deployed frontend origin.
- [ ] **Secret Hygiene**: Inspect client network tab; verify database URI and JWT secret are NEVER exposed in response payloads or client bundle.

---

## Automated Test Suite

Run the complete 47-test automated backend test suite:
```bash
./backend/venv/bin/pytest -v
```
Coverage includes:
- Health & readiness dependency verification
- MongoDB disconnected mode graceful degradation
- Telemetry ingestion validation and sanitization
- Detection rules and threshold evaluation
- Alert deduplication and status preservation
- Bcrypt password hashing and verification
- JWT issuance, verification, and expiration
- Role-based access control (Admin vs. Analyst)
- Rate limiting enforcement (HTTP 429)
- Request size protection and chunked file streaming (HTTP 413)
- Security headers and request ID tracking
- Audit logging integrity and password scrubbing
