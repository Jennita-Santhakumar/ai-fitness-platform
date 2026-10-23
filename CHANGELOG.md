# Changelog

All notable changes to the **AI Fitness Platform** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-24

### Added
- **Security & Rate Limiting**: `slowapi` rate limiting across sensitive and heavy routes (`/auth/login`, `/auth/register`, `/plans/generate`, `/plans/generate-async`).
- **Input Bounds**: Strict Pydantic string length limits on all free-form fields to guard against prompt injection and resource exhaustion.
- **Production Architecture**: Complete system diagrams and component reference in `docs/architecture.md`.
- **Production Docker Compose**: `docker-compose.prod.yml` with health checks, `restart: always`, zero volume mounts, and Nginx reverse proxy.
- **Cloud Deployment Configurations**: `render.yaml` for one-click multi-service Render deploy and `Procfile` for Heroku/Railway dynos.
- **Automated Container Migrations**: `docker-entrypoint.sh` executing `alembic upgrade head` before process boot.
- **Evaluation Benchmark**: 30 diverse personas evaluating plan validity and constraint compliance with 100% adherence (`docs/eval_results.md`).
- **Comprehensive Test Suite**: 178 automated tests passing offline with 93% test coverage enforced in CI.

---

## [0.5.0] - 2026-10-23

### Added
- **ChromaDB Vector Store**: Semantic workout memory service (`app/services/memory.py`) with per-user isolated collections.
- **RAG Prompt Injection**: Dynamically retrieves recent workout and progression history to inject into LLM prompts.
- **USDA FoodData Central Integration**: Food search client with 1-day Redis caching (`app/nutrition/usda.py`).
- **Daily Food Logging**: Food intake logging with SQL `func.sum` macro aggregations (`calories`, `protein`, `carbs`, `fat`).
- **React Frontend (Vite)**: Full single-page application with JWT auth, Recharts performance dashboard, interactive plan generation, and Strava integration (`frontend/`).

---

## [0.3.0] - 2026-10-22

### Added
- **Celery & Redis Worker**: Asynchronous background job infrastructure (`app/worker.py`).
- **Async Plan Generation**: Non-blocking `POST /plans/generate-async` returning `task_id` for polling.
- **Celery Beat Schedules**: Daily morning briefing email and weekly review progression summary cron tasks.
- **Strava OAuth 2.0**: Connect user accounts, refresh expired tokens, and synchronize recent outdoor activities.

---

## [0.2.0] - 2026-10-20

### Added
- **Multi-Provider LLM Resilience**: Dynamic failover across Groq (Llama 3), Google Gemini, and local Ollama.
- **Self-Healing Retry Engine**: Pydantic schema validation error feedback loop retrying up to 2 times.
- **Strict Plan Schema**: Multi-week periodized workout plans enforcing week/day/set/rep structure.
- **Plan Persistence**: `PlanRecord` PostgreSQL model with JSON columns and user ownership isolation.

---

## [0.1.0] - 2026-10-18

### Added
- **FastAPI Core**: Modular architecture with health checks and SQLite/PostgreSQL support.
- **Database Migrations**: Alembic setup with `0001_initial_tables.py`.
- **Authentication**: User registration with bcrypt hashing and OAuth2 JWT access/refresh tokens.
- **Domain CRUD**: Workouts, exercises, and sessions with strict IDOR ownership isolation.
- **CI Pipeline**: Automated GitHub Actions testing workflow.
