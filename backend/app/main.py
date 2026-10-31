from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import match, opportunities, projects, sponsors

# Load backend/.env if present (LLM config lives there).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(
    title="Hack Teh Tarik API",
    version="0.3.0",
    description=(
        "Backend for the ASEAN Opportunity Finder plus the original sponsor "
        "matcher. Opportunity matching is deterministic rule-based scoring; "
        "the sponsor matcher optionally uses an LLM."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(sponsors.router, prefix="/api")
app.include_router(match.router, prefix="/api")
app.include_router(opportunities.router, prefix="/api")


@app.get("/", tags=["meta"])
def root():
    return {
        "message": "Hack Teh Tarik API",
        "docs": "/docs",
        "endpoints": [
            "GET /api/opportunities",
            "GET /api/opportunities/{id}",
            "POST /api/opportunities/match",
            "GET /api/projects",
            "GET /api/projects/{id}",
            "POST /api/projects",
            "GET /api/sponsors",
            "POST /api/match",
            "POST /api/projects/{id}/match",
            "GET /api/llm/status",
        ],
    }


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}
