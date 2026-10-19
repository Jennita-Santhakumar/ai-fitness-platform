# AI Fitness Platform

An intelligent, multi-tier full-stack fitness and nutrition platform powered by FastAPI, PostgreSQL, Celery/Redis, ChromaDB, and multi-provider LLM plan generation.

## Project Structure
```
├── app/
│   ├── api/          # API endpoints & routers (auth, users, workouts, sessions, plans)
│   ├── core/         # Config, security, exceptions, and database session setup
│   ├── llm/          # Multi-provider LLM engine (Groq, Gemini, Ollama failover)
│   ├── models/       # SQLAlchemy ORM models (User, Workout, Exercise, Session, PlanRecord)
│   ├── schemas/      # Pydantic validation & serialization schemas
│   └── main.py       # FastAPI application entrypoint
├── tests/            # Automated test suite (pytest: 50+ unit and integration tests)
├── alembic/          # Database migration scripts
├── docs/             # Architecture, prompt evaluations, and prompt logs
├── scripts/          # Benchmark and verification scripts
├── requirements.txt  # Python dependencies
├── .env.example      # Sample environment variables
└── ROADMAP.md        # 35-day step-by-step progress tracker
```

## AI Workout Plan Generation (Milestone 2)

The platform features an enterprise-grade LLM generation and resilience pipeline:

* **Unified Provider Interface (`LLMProvider`)**: Strategy pattern abstracting cloud and on-premise AI models.
* **Supported Providers**:
  * **Groq**: Ultra-fast cloud inference running Llama 3 with low temperature (0.2).
  * **Google Gemini**: Cloud inference via Google Generative Language API.
  * **Ollama**: Offline, zero-cost fallback running locally at `http://localhost:11434`.
* **Reliability & Resilience Engine (`app/llm/resilience.py`)**:
  * **20s Enforced Timeout**: Prevents hung HTTP requests from blocking backend threads.
  * **Automated Failover Chain**: Sequentially tries `Groq ➔ Gemini ➔ Ollama`.
  * **Self-Correcting Retry Loop**: On schema violation or JSON syntax errors, appends the exact Pydantic error back to the model and retries up to 2 times.
  * **HTTP 502 Bad Gateway Mapping**: Cleanly handles total provider outages without crashing the API.
* **Strict Pydantic Validation (`app/schemas/plan.py`)**:
  * Multi-week structure (`Plan ➔ Week ➔ Day ➔ ExerciseItem`).
  * Enforces constraints: 1-12 weeks, 1-7 days/week, sets/reps > 0.
  * Auto-generates standard JSON Schema injected directly into system prompts.
* **Persistence & Endpoints**:
  * `POST /plans/generate`: Authenticated generation and storage in PostgreSQL (`JSON` columns).
  * `GET /plans`: Paginated history of generated plans.
  * `GET /plans/{id}`: Detailed view with strict row-level ownership isolation (404 on cross-user access).

## Quickstart
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run database migrations:
   ```bash
   alembic upgrade head
   ```
4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open the interactive API documentation:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Testing
Run the complete automated offline test suite (no real API keys or external services required):
```bash
pytest -v
```
