# AI Fitness Platform — System Architecture

## Overview

The AI Fitness Platform is a full-stack, production-grade fitness intelligence system built around FastAPI, PostgreSQL, Celery, Redis, ChromaDB, and a multi-provider LLM resilience layer. Below is the complete system diagram and component reference.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT TIER                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  React + Vite SPA (port 5173 dev / port 80 docker nginx)            │   │
│  │  Pages: Login · Register · Dashboard · Plans · Sessions · Nutrition  │   │
│  │  Auth: JWT Bearer intercepted by Axios (AuthContext + localStorage)  │   │
│  │  Charts: Recharts (weekly calorie / macro area chart)                │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │ HTTP/REST (JSON)                            │
└───────────────────────────────┼─────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             API TIER (port 8000)                             │
│  FastAPI application — uvicorn ASGI server                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Rate Limiting: slowapi (IP-keyed, 120 req/min default)              │  │
│  │  Auth: JWT (python-jose) — 30 min access + 7 day refresh tokens     │  │
│  │  Passwords: bcrypt (passlib)                                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Routers:                                                                   │
│  ┌─────────────┐ ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐  │
│  │ /auth       │ │ /workouts │ │ /sessions│ │ /plans    │ │ /nutrition│  │
│  │ register    │ │ CRUD      │ │ CRUD     │ │ generate  │ │ search    │  │
│  │ login       │ │ ownership │ │ Strava   │ │ generate  │ │ food log  │  │
│  │ refresh     │ │ isolation │ │ sync     │ │ -async    │ │ daily sum │  │
│  └─────────────┘ └───────────┘ └──────────┘ └───────────┘ └───────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  LLM Resilience Engine (app/llm/resilience.py)                       │  │
│  │  Failover chain: Groq ➔ Gemini ➔ Ollama                             │  │
│  │  Per-attempt: 20s timeout · up to 2 self-healing retries on schema   │  │
│  │  violation · HTTP 502 on total outage                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  RAG Memory Layer (app/services/memory.py + ChromaDB)                │  │
│  │  Per-user isolated vector collections · semantic retrieval           │  │
│  │  Injected into LLM system prompts for progressive plan generation    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────┬──────────────────────────┬──────────────────────────┬────────────────┘
       │                          │                          │
       ▼                          ▼                          ▼
┌──────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│  PostgreSQL  │       │  Redis (6379)    │       │  ChromaDB           │
│  (port 5432) │       │  Celery broker   │       │  (persisted volume) │
│              │       │  & result backend│       │  Per-user workout   │
│  Tables:     │       │  USDA nutrition  │       │  memory vectors     │
│  users       │       │  cache (1-day TTL│       └─────────────────────┘
│  workouts    │       │  per food ID)    │
│  exercises   │       └─────────┬────────┘
│  sessions    │                 │
│  plan_records│       ┌─────────▼────────────────────────────────────┐
│  food_logs   │       │  Celery Workers + Beat Scheduler              │
└──────────────┘       │  Tasks:                                       │
                       │  · generate_plan_task (async plan generation) │
                       │  · daily_briefing_task (morning summary)      │
                       │  · weekly_review_task (progress review)       │
                       └───────────────────────────────────────────────┘

External Integrations:
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│ Strava API       │  │ USDA FoodData    │  │ LLM Providers            │
│ OAuth 2.0        │  │ Central API      │  │ Groq · Gemini · Ollama   │
│ Activity sync    │  │ Nutrition search │  │                          │
└──────────────────┘  └──────────────────┘  └──────────────────────────┘
```

## Component Reference

### API Layer (`app/`)

| Module | Purpose |
|--------|---------|
| `app/main.py` | FastAPI app factory — registers all routers, slowapi middleware, CORS |
| `app/api/auth.py` | `/auth` — register, login (JWT), refresh token |
| `app/api/workouts.py` | `/workouts` — CRUD with ownership isolation (returns 404 on cross-user) |
| `app/api/sessions.py` | `/sessions` — Workout session logging, Strava OAuth callback + sync |
| `app/api/plans.py` | `/plans` — Sync and async AI plan generation with failover LLM engine |
| `app/api/nutrition.py` | `/nutrition` — USDA food search, food logging, daily macro summaries |
| `app/api/users.py` | `/users/me` — Authenticated user profile |
| `app/api/tasks.py` | `/tasks/{task_id}` — Celery task status polling |
| `app/core/config.py` | Pydantic settings (env vars, DB/Redis URLs, secrets) |
| `app/core/security.py` | bcrypt hashing, JWT create/decode, `get_current_user` dependency |
| `app/core/limiter.py` | slowapi `Limiter` instance — IP-keyed, 120 req/min default |
| `app/core/db.py` | SQLAlchemy engine, SessionLocal, `get_db` dependency |

### LLM Layer (`app/llm/`)

| Module | Purpose |
|--------|---------|
| `app/llm/base.py` | Abstract `LLMProvider` strategy interface |
| `app/llm/groq_provider.py` | Groq cloud inference (Llama 3, temp=0.2, 20s timeout) |
| `app/llm/gemini_provider.py` | Google Gemini inference |
| `app/llm/ollama_provider.py` | Ollama local inference fallback |
| `app/llm/prompts.py` | System prompts with RAG history injection |
| `app/llm/resilience.py` | `generate_plan_with_failover` — 3-provider chain with self-correcting retries |

### Data Layer (`app/models/` + `app/schemas/`)

| Model | Key Columns |
|-------|------------|
| `User` | id, email, hashed_password, is_active, strava_access_token, strava_refresh_token |
| `Workout` | id, user_id (FK), title, notes, created_at |
| `Exercise` | id, workout_id (FK), name, sets, reps, weight |
| `WorkoutSession` | id, user_id (FK), workout_id (FK), duration_minutes, notes, strava_activity_id |
| `PlanRecord` | id, user_id (FK), inputs (JSON), plan (JSON), provider, is_active, start_date |
| `FoodLog` | id, user_id (FK), food_id, food_name, calories, protein_g, carbs_g, fat_g, logged_at |

### Background Workers (`app/worker.py`)

| Task | Schedule | Purpose |
|------|----------|---------|
| `generate_plan_task` | On-demand (async) | LLM plan generation in background, stored to DB |
| `daily_briefing_task` | Cron: 06:00 daily | Morning workout summary email |
| `weekly_review_task` | Cron: Sunday 08:00 | Weekly performance review and progression analysis |

### Alembic Migrations (`alembic/versions/`)

| File | Description |
|------|-------------|
| `0001_initial_tables.py` | users, workouts, exercises, sessions |
| `0002_add_strava_fields.py` | Strava OAuth tokens on users |
| `0003_add_plan_records.py` | plan_records table |
| `0004_add_session_strava_link.py` | strava_activity_id on sessions |
| `0005_add_session_activity_type.py` | activity_type on sessions |
| `0006_add_strava_sync_status.py` | sync metadata columns |
| `0007_add_food_logs_table.py` | food_logs table |

## API Endpoint Reference

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | None | Register new user (rate-limited: 15/min) |
| POST | `/auth/login` | None | OAuth2 password login → JWT tokens (rate-limited: 10/min) |
| POST | `/auth/refresh` | Refresh token | Exchange refresh token for new access token |

### Users
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/me` | Bearer | Get authenticated user profile |

### Workouts
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/workouts` | Bearer | Create workout |
| GET | `/workouts` | Bearer | List workouts (paginated) |
| GET | `/workouts/{id}` | Bearer | Get workout details with exercises |
| PATCH | `/workouts/{id}` | Bearer | Update workout |
| DELETE | `/workouts/{id}` | Bearer | Delete workout |
| POST | `/workouts/{id}/exercises` | Bearer | Add exercise to workout |
| GET | `/workouts/{id}/exercises` | Bearer | List exercises in workout |
| DELETE | `/workouts/{id}/exercises/{eid}` | Bearer | Delete exercise |

### Workout Sessions
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/sessions` | Bearer | Log a workout session |
| GET | `/sessions` | Bearer | List sessions (paginated) |
| GET | `/sessions/{id}` | Bearer | Get session details |
| PATCH | `/sessions/{id}` | Bearer | Update session |
| DELETE | `/sessions/{id}` | Bearer | Delete session |
| GET | `/sessions/strava/connect` | Bearer | Redirect to Strava OAuth |
| GET | `/sessions/strava/callback` | Bearer | Handle Strava OAuth callback |
| POST | `/sessions/strava/sync` | Bearer | Sync recent Strava activities |
| GET | `/sessions/strava/status` | Bearer | Check Strava connection status |

### AI Workout Plans
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/plans/generate` | Bearer | Sync AI plan generation (rate-limited: 10/min) |
| POST | `/plans/generate-async` | Bearer | Async plan generation (Celery, rate-limited: 15/min) |
| GET | `/plans` | Bearer | List generated plans (paginated) |
| GET | `/plans/{id}` | Bearer | Get specific plan |

### Nutrition
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/nutrition/search` | Bearer | Search USDA food database |
| GET | `/nutrition/food/{id}` | Bearer | Get food item details |
| POST | `/nutrition/log` | Bearer | Log a food entry |
| GET | `/nutrition/log` | Bearer | List food logs |
| GET | `/nutrition/summary` | Bearer | Daily macro summary (calories, protein, carbs, fat) |

### System
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check (API + DB connectivity) |
| GET | `/tasks/{task_id}` | Bearer | Celery task status polling |

## Security Controls

| Control | Implementation |
|---------|---------------|
| Password hashing | bcrypt with random salt (passlib) |
| Access tokens | HS256 JWT, 30-minute expiry |
| Refresh tokens | HS256 JWT, 7-day expiry, `type=refresh` claim |
| Row-level isolation | All queries filter by `user_id = current_user.id` |
| IDOR prevention | Cross-user access returns 404 (not 403) to prevent enumeration |
| Rate limiting | slowapi IP-keyed: 10/min login, 15/min register, 120/min default |
| Input validation | Pydantic field constraints (min_length, max_length, ge, le) |
| Secret storage | `.env` file only — never committed; `.env.example` for documentation |

## Frontend Architecture (`frontend/`)

```
frontend/src/
├── api.js                    # Axios instance with JWT interceptor + auto-refresh
├── context/AuthContext.jsx   # Global auth state (login, logout, token storage)
├── components/
│   ├── Navbar.jsx            # Navigation + logout button
│   └── ProtectedRoute.jsx    # Redirects unauthenticated users to /login
└── pages/
    ├── Login.jsx             # Email/password login form
    ├── Register.jsx          # Registration form
    ├── Dashboard.jsx         # Recharts area chart, Strava status, summary stats
    ├── Plans.jsx             # Plan generation form with async polling
    ├── Sessions.jsx          # Session log + Strava sync button
    └── Nutrition.jsx         # Food search, log meals, daily macro display
```
