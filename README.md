# AI Fitness Platform

An intelligent, multi-tier full-stack fitness and nutrition platform powered by FastAPI, PostgreSQL, Celery/Redis, ChromaDB, and multi-provider LLM plan generation.

## Project Structure
```
├── app/
│   ├── api/          # API endpoints & routers
│   ├── core/         # Config, security, and database session setup
│   ├── models/       # SQLAlchemy ORM models
│   ├── schemas/      # Pydantic validation & serialization schemas
│   └── main.py       # FastAPI application entrypoint
├── tests/            # Automated test suite (pytest)
├── alembic/          # Database migration scripts
├── requirements.txt  # Python dependencies
├── .env.example      # Sample environment variables
└── ROADMAP.md        # 35-day step-by-step progress tracker
```

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
3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open the interactive API documentation:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
