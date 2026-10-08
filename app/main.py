from fastapi import FastAPI

app = FastAPI(
    title="AI Fitness Platform API",
    description="Backend API for AI-powered workout planning, nutrition tracking, and analytics.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify that the API server is up and responsive."""
    return {"status": "ok"}
