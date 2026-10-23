# AI Fitness Platform

[![CI](https://github.com/ai-fitness/ai-fitness-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/ai-fitness/ai-fitness-platform/actions)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](https://github.com/ai-fitness/ai-fitness-platform)
[![Tests](https://img.shields.io/badge/tests-178%20passed-success.svg)](https://github.com/ai-fitness/ai-fitness-platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent, enterprise-grade full-stack fitness and nutrition platform built with **FastAPI**, **PostgreSQL**, **Celery + Redis**, **ChromaDB**, **React (Vite)**, and multi-provider LLM plan generation with self-healing failover.

---

## Architecture Overview

```
                      ┌───────────────────────────────┐
                      │    React + Vite Single-Page   │
                      │    Application (port 5173/80) │
                      └──────────────┬────────────────┘
                                     │ HTTP / REST (JWT Auth)
                                     ▼
                      ┌───────────────────────────────┐
                      │     FastAPI Backend (8000)    │
                      │  Rate limiting · Pydantic v2  │
                      │  Row-level ownership (IDOR)   │
                      └──────┬──────────────┬─────────┘
                             │              │
              ┌──────────────┴──────┐       │ Celery Tasks
              ▼                     ▼       ▼
       ┌──────────────┐      ┌─────────────┐┌────────────────────────┐
       │  PostgreSQL  │      │  ChromaDB   ││  Redis 7 (Broker &     │
       │  Database    │      │  Vector RAG ││  USDA Nutrition Cache) │
       └──────────────┘      └─────────────┘└──────────┬─────────────┘
                                                       │
                                            ┌──────────▼─────────────┐
                                            │ Celery Worker & Beat   │
                                            │ Async plans · Cron     │
                                            └────────────────────────┘
```

Detailed component specifications, sequence diagrams, and table relationships are in [docs/architecture.md](docs/architecture.md).

---

## Key Features

* **AI Workout Plan Generation**: Multi-week periodized plans generated with self-healing retry loops and an automatic failover chain across **Groq (Llama 3)** ➔ **Google Gemini** ➔ **Ollama** (offline fallback).
* **RAG-Powered Memory**: Per-user isolated ChromaDB vector stores inject recent workout history and progression notes directly into LLM prompts.
* **USDA Food & Nutrition Tracking**: Search FoodData Central with 1-day Redis caching, log daily meals, and compute SQL-aggregated daily macro breakdowns (calories, protein, carbs, fat).
* **Strava Integration**: OAuth 2.0 flow with automatic token refreshes and background synchronization for runs, rides, and workouts.
* **Background Jobs**: Asynchronous Celery tasks for heavy plan generation, plus scheduled morning briefings and weekly reviews via Celery Beat.
* **Hardened Security**: IP-based rate limiting via `slowapi`, bcrypt password hashing, dual JWT tokens (access + refresh), strict row-level ownership isolation (returns 404 to avoid enumeration), and Pydantic input length guards.
* **Modern React UI**: Vite + React single-page app featuring dark-mode design, Recharts interactive macro dashboards, real-time async task polling, and Strava connection management.

---

## Quickstart

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- Docker and Docker Compose (recommended)

### Option A: Docker Compose (Fastest)

```bash
# 1. Clone and copy environment variables
git clone https://github.com/ai-fitness/ai-fitness-platform.git
cd ai-fitness-platform
cp .env.example .env

# 2. Start all services (PostgreSQL, Redis, API, Worker, Beat, Frontend)
docker compose up -d

# 3. Open the apps:
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### Option B: Local Development Setup

```bash
# 1. Setup Python virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start local Postgres & Redis
docker run -d --name test_pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine
docker run -d --name test_redis -p 6379:6379 redis:7-alpine

# 4. Run database migrations
alembic upgrade head

# 5. Start the backend API server
uvicorn app.main:app --reload --port 8000

# 6. Start Celery worker (in a separate terminal)
celery -A app.worker.celery_app worker --loglevel=info

# 7. Start the frontend
cd frontend
npm install
npm run dev
# Frontend runs at http://localhost:5173
```

---

## API Reference

Interactive OpenAPI documentation is live at `/docs` (Swagger UI) and `/redoc` (ReDoc).

### Authentication (`/auth`)
| Method | Path | Rate Limit | Description |
|--------|------|------------|-------------|
| `POST` | `/auth/register` | 15/min | Create new account with bcrypt password |
| `POST` | `/auth/login` | 10/min | OAuth2 password flow returning access + refresh JWTs |
| `POST` | `/auth/refresh` | — | Exchange refresh token for fresh access token |

### Workouts & Exercises (`/workouts`)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/workouts` | Create workout routine |
| `GET` | `/workouts` | List workouts (supports `limit` and `offset`) |
| `GET` | `/workouts/{id}` | Get workout details with exercises |
| `PATCH` | `/workouts/{id}` | Update workout title or notes |
| `DELETE` | `/workouts/{id}` | Delete workout (cascades to exercises) |
| `POST` | `/workouts/{id}/exercises` | Add exercise to routine |
| `GET` | `/workouts/{id}/exercises` | List exercises in routine |
| `DELETE` | `/workouts/{id}/exercises/{eid}` | Delete specific exercise |

### Workout Sessions & Strava (`/sessions`)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sessions` | Log a completed session |
| `GET` | `/sessions` | List user sessions |
| `GET` | `/sessions/{id}` | Get session details |
| `PATCH` | `/sessions/{id}` | Update session metrics |
| `DELETE` | `/sessions/{id}` | Delete session |
| `GET` | `/sessions/strava/connect` | Initiate Strava OAuth 2.0 flow |
| `GET` | `/sessions/strava/callback`| Handle Strava authorization callback |
| `POST` | `/sessions/strava/sync` | Trigger sync of recent Strava activities |
| `GET` | `/sessions/strava/status` | Check user Strava connection state |

### AI Workout Plans (`/plans`)
| Method | Path | Rate Limit | Description |
|--------|------|------------|-------------|
| `POST` | `/plans/generate` | 10/min | Synchronous plan generation with LLM failover |
| `POST` | `/plans/generate-async`| 15/min | Enqueue generation in Celery background worker |
| `GET` | `/plans` | — | Paginated history of generated plans |
| `GET` | `/plans/{id}` | — | Get plan details (enforces user ownership) |

### Nutrition (`/nutrition`)
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/nutrition/search` | Search USDA FoodData Central (Redis-cached) |
| `GET` | `/nutrition/food/{fdc_id}` | Fetch detailed food nutrition facts |
| `POST` | `/nutrition/log` | Record a meal or food item |
| `GET` | `/nutrition/log` | List food logs (filterable by date) |
| `GET` | `/nutrition/summary` | Aggregated daily calories, protein, carbs, and fat |

### System & Tasks
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check with live PostgreSQL `SELECT 1` ping |
| `GET` | `/tasks/{task_id}` | Poll background Celery task status |

---

## Production Deployment

### Production Docker Compose
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
Features:
- No volume mounts (immutable production containers)
- `restart: always` on all services
- Integrated health checks with automated restart dependencies
- Nginx frontend running on port 80

### One-Click Cloud Deployment (Render / Heroku)
The repository includes a ready-to-deploy configuration:
- `render.yaml`: Provisions PostgreSQL, Redis, FastAPI web service, Celery worker, Celery beat, and React static site with linked secrets.
- `Procfile`: Ready for Heroku or Railway web/worker dyno setups.

---

## Testing & Quality

The platform includes a comprehensive, 100% offline test suite (runs without real API keys or external services):

```bash
# Run the full test suite with coverage
pytest --cov=app --cov-report=term-missing

# Run a specific module
pytest tests/test_security_rate_limit.py -v
```

* **178 passing tests**
* **93% test coverage** enforced in CI (`--cov-fail-under=70`)
* Evaluated against 30 diverse personas in `docs/eval_results.md` (100% schema compliance)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
