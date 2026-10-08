# AI Fitness Platform: 35-Day Learning & Implementation Roadmap

## Milestone 1: Core API (Days 1–7)
- [x] **Day 1: Setup and scaffold**
  - Goal: Working dev environment and repository.
  - Commit: `chore: scaffold repo with health endpoint`
  - Learning Log:
    - Initialized modular FastAPI architecture (`app/api`, `app/core`, `app/models`, `app/schemas`).
    - Configured `.gitignore` to prevent leaking virtual envs (`.venv/`) and secrets (`.env`).
    - Verified `GET /health` endpoint functionality with automated `pytest` test suite.
- [ ] **Day 2: Docker Compose + database connection**
  - Goal: API and Postgres run together with one command.
  - Commit: `feat: dockerize api and postgres`
  - Learning Log:
- [ ] **Day 3: Models and migrations**
  - Goal: Database tables created through Alembic.
  - Commit: `feat(db): add models and initial migration`
  - Learning Log:
- [ ] **Day 4: Auth part 1: register**
  - Goal: Users can register with a hashed password.
  - Commit: `feat(auth): add user registration with bcrypt`
  - Learning Log:
- [ ] **Day 5: Auth part 2: login and JWT**
  - Goal: Login returns tokens; protected routes check them.
  - Commit: `feat(auth): add login, jwt tokens and current user dependency`
  - Learning Log:
- [ ] **Day 6: CRUD for workouts, exercises, sessions**
  - Goal: Authenticated users manage their own data.
  - Commit: `feat(api): add workout, exercise and session crud`
  - Learning Log:
- [ ] **Day 7: Tests, CI and tag v0.1**
  - Goal: 15+ tests, green CI, first release tag `v0.1`.
  - Commit: `test: add fixtures and ci workflow`
  - Learning Log:

## Milestone 2: LLM Plan Generation (Days 8–14)
- [ ] **Day 8: LLM client interface + Groq** (`feat(llm): add provider interface and groq client`)
- [ ] **Day 9: Gemini and Ollama providers** (`feat(llm): add gemini and ollama providers`)
- [ ] **Day 10: Plan schema** (`feat(plans): add plan pydantic schema`)
- [ ] **Day 11: Prompt templates + generation** (`feat(plans): add prompt templates and plan generation`)
- [ ] **Day 12: Reliability: retry, timeout, failover** (`feat(llm): add retry, timeout and provider failover`)
- [ ] **Day 13: Plan endpoints + storage** (`feat(plans): add plan endpoints and storage`)
- [ ] **Day 14: Mocked-LLM tests and tag v0.2** (`test(plans): add mocked llm tests`)

## Milestone 3: Background Jobs (Days 15–21)
- [ ] **Day 15: Redis + Celery hello world** (`feat(jobs): add celery and redis`)
- [ ] **Day 16: Async plan generation + status** (`feat(jobs): add async plan generation`)
- [ ] **Day 17: Daily briefing + beat** (`feat(jobs): add daily briefing task`)
- [ ] **Day 18: Weekly review** (`feat(jobs): add weekly review task`)
- [ ] **Day 19: Retries, idempotency, failure handling** (`feat(jobs): add retries and idempotency`)
- [ ] **Day 20: Strava OAuth** (`feat(integrations): add strava oauth`)
- [ ] **Day 21: Strava sync and tag v0.3** (`feat(integrations): add strava activity sync`)

## Milestone 4: Memory, Nutrition, Dashboard (Days 22–29)
- [ ] **Day 22: ChromaDB memory store** (`feat(memory): add chromadb memory store`)
- [ ] **Day 23: Retrieval in prompts** (`feat(plans): add memory retrieval to prompts`)
- [ ] **Day 24: USDA nutrition client** (`feat(nutrition): add usda client and search`)
- [ ] **Day 25: Nutrition log** (`feat(nutrition): add food log and daily summary`)
- [ ] **Day 26: React scaffold + auth** (`feat(ui): add react app with auth`)
- [ ] **Day 27: Plan and session pages** (`feat(ui): add plan and session pages`)
- [ ] **Day 28: Nutrition page + dashboard** (`feat(ui): add nutrition page and dashboard`)
- [ ] **Day 29: Integrate, polish, tag v0.5** (`chore: integrate and polish for v0.5`)

## Milestone 5: Quality and Ship (Days 30–35)
- [ ] **Day 30: Coverage and test gaps** (`test: improve coverage`)
- [ ] **Day 31: Plan-quality evaluation** (`feat(eval): add plan quality evaluation`)
- [ ] **Day 32: Security and robustness pass** (`fix(security): add rate limiting and input limits`)
- [ ] **Day 33: Production compose + docs** (`docs: add readme and architecture`)
- [ ] **Day 34: Deploy** (`chore: add deployment config`)
- [ ] **Day 35: Final polish and resume update, tag v1.0** (`docs: final polish for v1.0`)
