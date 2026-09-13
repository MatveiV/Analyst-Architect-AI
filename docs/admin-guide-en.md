# AnalystGuru Administrator Guide

> Version: 1.0.0 | Audience: System administrators, DevOps, Team leads

---

## Table of Contents

1. [Deployment Architecture](#1-deployment-architecture)
2. [Installation and Launch](#2-installation-and-launch)
3. [Role Model and Authorization](#3-role-model-and-authorization)
4. [User Management](#4-user-management)
5. [AI Provider Configuration](#5-ai-provider-configuration)
6. [Database](#6-database)
7. [Monitoring and Audit](#7-monitoring-and-audit)
8. [Security](#8-security)
9. [Infrastructure Diagrams](#9-infrastructure-diagrams)

---

## 1. Deployment Architecture

```
Internet
    │
    ▼
Nginx (port 3000) ──── React SPA (static files, login screen)
    │
    ▼
FastAPI (port 8000) ── JWT Auth + RBAC ── SQLite / PostgreSQL
    │
    ▼
LLM API (Anthropic / OpenAI / ProxyAPI)
```

### Minimum Server Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Disk | 10 GB | 20 GB SSD |
| Docker | 24.x | 25.x |

---

## 2. Installation and Launch

```bash
git clone <repo-url>
cd analyst-guru
cp .env.example .env
nano .env   # Insert API key and APP_SECRET_KEY

docker-compose up --build -d
curl http://localhost:8000/health
open http://localhost:3000
```

### Environment Variables (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `PROXYAPI_KEY` | LLM provider key | One of the three |
| `LLM_PROVIDER` | Active provider | ✅ |
| `APP_SECRET_KEY` | Secret key for JWT signing (min 32 chars) | ✅ |
| `DATABASE_URL` | Database URL | ✅ |
| `MAX_DOCUMENT_LENGTH` | Max document length | ❌ (30000) |
| `RAG_TOP_K` | Number of RAG fragments | ❌ (5) |
| `LLM_TIMEOUT` | Timeout for a single LLM call, seconds. For local models (Ollama) on modest hardware raise to 2400+, otherwise URS/SRS generation falls into the safe-fallback with `needs_review=true` | ❌ (600) |

### First Launch: Automatic Default Accounts

On first startup (`lifespan` in `main.py`), the system automatically seeds three default accounts:

```
admin      / admin123     → role: admin
analyst    / analyst123   → role: analyst
architect  / architect123 → role: architect
```

> ⚠️ **MANDATORY: change default passwords before production** (see Section 4).

---

## 3. Role Model and Authorization

### Authorization Mechanism

- Authentication: **username + password**, endpoint `POST /auth/login` (OAuth2PasswordRequestForm)
- Passwords are stored hashed via **bcrypt** (never in plain text)
- On success, a **JWT access token** is issued (HS256, 8-hour lifetime)
- Token is passed via `Authorization: Bearer <token>` header on every protected request
- Frontend stores the token in `localStorage`, auto-attaches it via an axios interceptor
- On expiry/invalid token, backend returns `401` → frontend clears session and returns to login

### Three Roles and Their Permissions

| Role | Permissions |
|------|-------------|
| `admin` | All business functions + `/auth/register`, `/auth/users`, `/settings/*` |
| `architect` | All business functions + `/settings/*` (AI provider configuration) |
| `analyst` | Documents, reviews, knowledge base, memory, audit (no settings/users) |

### How Role Checks Work on the Backend

Restrictions are declared **at the router level** in `app/main.py`, not per-endpoint — this guarantees a new endpoint can never be accidentally left unprotected:

```python
app.include_router(documents.router,       dependencies=[Depends(require_analyst)])
app.include_router(reviews.router,         dependencies=[Depends(require_analyst)])
app.include_router(knowledge_base.router,  dependencies=[Depends(require_analyst)])
app.include_router(memory.router,          dependencies=[Depends(require_analyst)])
app.include_router(diagrams.router,        dependencies=[Depends(require_analyst)])
app.include_router(audit.router,           dependencies=[Depends(require_analyst)])
app.include_router(settings_router.router, dependencies=[Depends(require_architect)])
```

`require_analyst` allows any of the three roles. `require_architect` allows only architect and admin. `/auth/register` and `/auth/users*` are individually protected with `Depends(require_admin)`.

### Verifying Protection

```bash
# Without token — 401
curl -i http://localhost:8000/documents

# With analyst token — 200
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -d "username=analyst&password=analyst123" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/documents

# Analyst tries settings — 403
curl -i -H "Authorization: Bearer $TOKEN" http://localhost:8000/settings/providers
```

---

## 4. User Management

### Via Web Interface

Log in as `admin` → **👥 Users** → **+ Add User**.

### Via REST API

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/auth/register \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"analyst2","email":"analyst2@company.com","password":"Str0ng!Pass","full_name":"Jane Smith","role":"analyst"}'

curl http://localhost:8000/auth/users -H "Authorization: Bearer $TOKEN"

curl -X PATCH http://localhost:8000/auth/users/{USER_ID} \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"role":"architect"}'

curl -X POST http://localhost:8000/auth/users/{USER_ID}/reset-password \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"new_password":"NewStr0ng!Pass"}'
```

---

## 5. AI Provider Configuration

Available to **architect and admin roles only** (analyst gets 403).

```bash
curl -X POST http://localhost:8000/settings/providers \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"provider":"anthropic","api_key":"sk-ant-...","model":"claude-sonnet-4-20250514","temperature":0.2,"max_tokens":4096}'

curl -X POST "http://localhost:8000/settings/providers/activate?provider=anthropic" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "http://localhost:8000/settings/test?provider=anthropic" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 6. Database

```sql
-- Users / RBAC
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,  -- bcrypt hash
    role VARCHAR(20) DEFAULT 'analyst',     -- admin|analyst|architect
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME
);

-- Variant 2: reviewed specs (migration 0007_split_documents)
CREATE TABLE spec_documents (...);  -- id, created_at, title, text, doc_type, project_name
CREATE TABLE reviews (...);         -- review_json, needs_review, confidence, error (reason)

-- Variant 5: team knowledge base
CREATE TABLE kb_documents (...);    -- id, created_at, title, text, project_name, source_type, source_id
CREATE TABLE kb_snippets (...);     -- RAG chunks (document_id -> kb_documents)
CREATE TABLE qa_runs (...);         -- question, answer, sources_json, needs_review, error

-- Shared audit of every operation in both variants
CREATE TABLE audit_runs (...);      -- action, input, output, status, error, duration_ms
```

### Local Windows Launch (without Docker)

```bat
:: 1) backend (FastAPI :8000)
C:\GitHub\3A\backend\run_backend.bat
:: 2) frontend (Vite :3000)
C:\GitHub\3A\frontend\run_vite.bat
:: or both at once: start_services.bat (repository root)
```

> ⚠️ Always launch via the bat files: they run `cd /d C:\GitHub\3A\backend` /
> `cd /d C:\GitHub\3A\frontend`. Launching `wmic process call create "python -m uvicorn ..."`
> directly starts the process with the working directory `C:\Windows\system32`, so the relative
> path `sqlite:///./data/...` does not resolve and every DB request fails with 500.

### Troubleshooting Common Issues (verified on a local run)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `POST /documents/{id}/generate-urs` (and `srs`) returns `needs_review=true` with empty fields | LLM call exceeded the openai SDK timeout (600s) → safe-fallback | Raise `LLM_TIMEOUT` in `.env` (2400+) and restart the backend |
| `GET /documents/{id}/export/{markdown,docx,full-package/docx}` → 500 | Cyrillic in the document title inside the `Content-Disposition` header (HTTP headers are latin-1 only) | Fixed in `documents.py`: uses `filename*=UTF-8''` (RFC 5987) — update the code to the current version |
| Every API request → 500 "unable to open database file" | Server launched with a wrong working directory | Launch via `run_backend.bat` |
| Diagrams stuck in `external_fallback` status | Kroki unavailable (default `http://kroki:8000` is a docker-internal name) | Start Kroki (`docker run yuzutech/kroki`) and set `DIAGRAM_RENDERER_URL=http://127.0.0.1:8001` |
| First KB document upload is slow (1–2 min) | Embedding model `all-MiniLM-L6-v2` (sentence-transformers) is being downloaded | One-time; subsequent uploads are fast |

### Backup

```bash
cp data/analyst_architect_ai.db backups/analyst_architect_ai_$(date +%Y%m%d_%H%M%S).db
sqlite3 data/analyst_architect_ai.db "SELECT username, role, is_active FROM users;"
```

### Switching to PostgreSQL

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/analyst_architect_ai
```

---

## 7. Monitoring and Audit

```bash
curl http://localhost:8000/audit/stats -H "Authorization: Bearer $TOKEN"
```

| Metric | Normal | Warning | Problem |
|--------|--------|---------|---------|
| `error_rate_pct` | < 5% | 5–15% | > 15% |
| `needs_review_pct` | < 20% | 20–40% | > 40% |

---

## 8. Security

### Production Checklist

- [ ] Change all default passwords
- [ ] Generate `APP_SECRET_KEY`: `openssl rand -hex 32`
- [ ] Configure HTTPS
- [ ] Restrict `CORS allow_origins`
- [ ] Firewall: only 80/443 open
- [ ] Switch to PostgreSQL for production load
- [ ] Regular database backups
- [ ] API keys in secrets manager
- [ ] `APP_SECRET_KEY` rotation every 90 days (invalidates all current tokens)

### JWT Implementation Notes

- Algorithm: HS256 (symmetric, single secret across backend)
- Token lifetime: 8 hours
- No refresh-token mechanism in v1.0 — re-login required after expiry
- Token embeds `sub` (user_id) and `role`; `is_active` is still re-checked against the DB on every request via `get_current_user`

---

## 9. Infrastructure Diagrams

### Deployment Diagram

```mermaid
graph TB
    subgraph Client["🖥️ Client"]
        Browser["Browser\nhttps://host:3000"]
    end

    subgraph Server["🖥️ Server / VPS (Docker Compose)"]
        Nginx["nginx:alpine\nPort 3000\nSPA + /api proxy"]
        FastAPI["python:3.11-slim\nPort 8000\n15 routers · JWT+RBAC\nFAISS indices in-memory"]
        Kroki["yuzutech/kroki:0.25\nPort 8001\nLocal render\nPlantUML/Mermaid/GraphViz"]
        Ollama["ollama/ollama\nPort 11434\nlocal-llm profile\n(optional)"]
        DB[("SQLite / PostgreSQL\n25 models · 7 Alembic migrations\nvolume: ./data")]
        VolOllama[("ollama_models\nnamed volume")]
    end

    subgraph External["☁️ External LLM services"]
        Claude["Anthropic Claude"]
        OpenAI["OpenAI"]
        ProxyAPI["ProxyAPI (RU)"]
        OpenRouter["OpenRouter"]
    end

    Browser -->|"HTTPS :443"| Nginx
    Nginx -->|"HTTP API :8000"| FastAPI
    FastAPI -->|"SQLAlchemy async"| DB
    FastAPI -->|"HTTP :8001\ndiagram render"| Kroki
    FastAPI -.->|"HTTP :11434\n(local-llm profile)"| Ollama
    Ollama --- VolOllama

    FastAPI -->|"HTTPS REST"| Claude
    FastAPI -->|"HTTPS REST"| OpenAI
    FastAPI -->|"HTTPS REST"| ProxyAPI
    FastAPI -->|"HTTPS REST"| OpenRouter

    note["⬛ ENFORCE_LOCAL_ONLY=true → all outbound HTTPS to external LLMs is blocked;\nonly local Ollama + Kroki remain (air-gapped mode)"]
    FastAPI -.->|"honors flag"| note
```

**Volumes:** `./data` (bind-mount, SQLite + `analyst_architect_ai.db`) and `ollama_models` (named volume, Ollama models).

**docker-compose profiles:**
- by default `backend`, `frontend`, `kroki` start (kroki is lightweight, always-on);
- `ollama` — only with `--profile local-llm`;
- if Ollama is already on the host, skip the profile and set `OLLAMA_BASE_URL=http://host.docker.internal:11434` (Win/Mac) or `http://172.17.0.1:11434` (Linux).

### Sequence: JWT Auth + RBAC Check

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as FastAPI
    participant Dep as require_analyst / require_architect
    participant DB as Database

    U->>FE: Enters username/password
    FE->>API: POST /auth/login
    API->>DB: SELECT user, bcrypt.verify
    API->>API: jwt.encode({sub: user_id, role})
    API-->>FE: access_token

    Note over FE,API: All subsequent requests
    FE->>API: GET /settings/providers\nAuthorization: Bearer <token>
    API->>Dep: Role check
    Dep->>API: jwt.decode(token) → user_id, role
    Dep->>DB: SELECT user WHERE id=? (checks is_active)
    alt role in [architect, admin]
        Dep-->>API: OK, pass through
        API->>DB: SELECT * FROM provider_settings
        API-->>FE: 200 + 5-provider config
    else role == analyst
        Dep-->>API: 403 Forbidden
        API-->>FE: 403
    end
```
