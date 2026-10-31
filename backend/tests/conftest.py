"""Shared pytest setup for the backend test suite."""

import os

# Force the heuristic engine in tests so no network call or API key is needed.
# This must happen before `app.main` imports and loads backend/.env.
os.environ.setdefault("LLM_PRESET", "none")
