# hack-teh-tarik

Hacktoberfest KL 2026 project. This branch contains the backend of the
Sponsor Matcher API: FastAPI app that stores hackathon projects, lists
sponsors, and ranks projects against sponsor tracks with an optional
LLM-powered engine (heuristic fallback built in).

## Backend quickstart

Requires Python 3.11+.

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) configure an LLM provider
copy .env.example .env            # then fill in keys; see comments inside

# 4. Run the API
uvicorn app.main:app --reload
#    -> http://127.0.0.1:8000/docs
```

Without a `.env` (or with no API key) everything still works: matching runs
on the built-in heuristic engine. `GET /api/llm/status` shows the active mode.

## Key endpoints

| Method | Path                          | Description                              |
| ------ | ----------------------------- | ---------------------------------------- |
| GET    | `/api/health`                 | Liveness check                           |
| GET    | `/api/llm/status`             | Active matching mode and LLM config      |
| GET    | `/api/sponsors`               | All sponsors                             |
| GET    | `/api/projects`               | Projects (supports `q`, `domain`, `tech`, `experience`, `limit`) |
| POST   | `/api/projects`               | Submit a project                         |
| POST   | `/api/match`                  | Match an inline project draft            |
| POST   | `/api/projects/{id}/match`    | Match a stored project (JSON body or `top_k`/`user_context` query params) |

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest        # from the backend/ directory
```

Tests run fully offline (the heuristic engine is forced via the test
conftest) and restore `app/data/projects.json` after write tests.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) on `main`. Commits follow the
[Conventional Commits](https://www.conventionalcommits.org/) convention.

## License

MIT — see [LICENSE](LICENSE).
