# ASEAN Opportunity Finder — Integrated Prototype

A hackathon prototype that helps early-stage ASEAN founders find support programmes that
might fit their startup, and explains **why** each one was suggested.

The project combines two development branches:

- a browser frontend (HTML/CSS/vanilla JavaScript), and
- a FastAPI backend that owns the opportunity records and the matching rules.

> **Demo data only.** The 12 opportunity records are fictional examples written for the
> hackathon. They are **not** real programmes, providers, deadlines, or eligibility rules.
> Nothing here proves that any opportunity exists or is currently open.

---

## 1. The problem

ASEAN founders are often told that funding and support exist, but the details are scattered,
inconsistent, and rarely explain *why* a particular programme fits a particular startup.
Early-stage teams waste time on opportunities they were never eligible for, and they cannot
easily tell verified information from guesswork.

## 2. Who it is for

- First-time founders and student teams in ASEAN
- Very early teams (idea, pre-seed, seed) without advisers or networks
- Hackathon judges and mentors evaluating how transparent matching could work

This is **not** an official directory and **not** financial or legal advice.

## 3. Features

1. Enter **country, industry, company stage, and goals** (all optional).
2. The backend scores every opportunity with **fixed, explainable rules** and returns
   plain-language reasons for each score.
3. Cards show **deadline, eligibility, source URL, and verification status**, including
   explicit "Unknown" states instead of guesses.
4. Filter by **type** and **record status** (verified / demo), search, and sort.
5. A **data check** panel validates the records received from the backend.
6. Clear **loading, empty, and API-error** states. If the backend is unavailable the page
   shows an error and a retry button instead of silently showing stale data.
7. The original **sponsor matcher API** (projects, sponsors, optional LLM matching) is kept
   and still works independently.

## 4. Architecture

```
Browser: index.html + styles.css + app.js
    |
    |  GET  /api/opportunities
    |  POST /api/opportunities/match
    v
FastAPI backend (backend/app)
    |-- routers/opportunities.py      list + match + lookup routes
    |-- opportunity_matching.py       deterministic rule engine
    |-- models.py                     Pydantic schema (camelCase JSON)
    |-- store.py                      reads JSON files (no database)
    `-- data/opportunities.json       single source of opportunity records
```

The legacy sponsor matcher is unchanged and lives beside it:

```
routers/projects.py, routers/sponsors.py, routers/match.py
matching.py (sponsor heuristic), llm.py (optional OpenAI-compatible client)
data/projects.json, data/sponsors.json
```

There is **no database** and no build step. `data.js` is kept as the original offline
snapshot for reference, but the page no longer loads it; the backend JSON file is the source
of truth.

## 5. Repository layout

```
hack-teh-tarik/
├─ index.html            Page: startup form, filters, results, data-check panel
├─ styles.css            Responsive styling
├─ app.js                API calls, validation, filtering, rendering
├─ data.js               Original offline demo snapshot (reference only)
├─ README.md             This file
├─ LICENSE               MIT license (unchanged)
└─ backend/
   ├─ app/
   │  ├─ main.py         FastAPI app and CORS
   │  ├─ models.py       Pydantic models
   │  ├─ store.py        JSON storage helpers
   │  ├─ matching.py     Sponsor matcher (heuristic + optional LLM)
   │  ├─ opportunity_matching.py   Opportunity rule engine
   │  ├─ llm.py          Optional LLM client
   │  ├─ routers/        API routes
   │  └─ data/           opportunities.json, projects.json, sponsors.json
   ├─ tests/             Pytest suite (27 tests)
   ├─ requirements.txt
   ├─ requirements-dev.txt
   └─ .env.example
```

## 6. Prerequisites

- **Windows 11** (macOS/Linux work too; commands below are for Windows).
- **Python 3.11 or newer** on `PATH` (`python --version`).
- A modern browser (Edge, Chrome, or Firefox).
- No Node.js, npm, database, or build tools.

If `python` opens the Microsoft Store instead of showing a version, install Python 3.11+
from <https://www.python.org/downloads/windows/> and tick **Add python.exe to PATH**.

## 7. Run on Windows 11 (exact commands)

Use **two PowerShell terminals**. Start the backend first.

### Terminal 1 — backend

```powershell
cd "C:\Users\60122\Documents\Hacktoberfest 2026\hack-teh-tarik\backend"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, skip it and call the venv interpreter directly:

```powershell
cd "C:\Users\60122\Documents\Hacktoberfest 2026\hack-teh-tarik\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend is ready when it prints `Uvicorn running on http://127.0.0.1:8000`.
Leave this terminal open.

### Terminal 2 — frontend

```powershell
cd "C:\Users\60122\Documents\Hacktoberfest 2026\hack-teh-tarik"
python -m http.server 5500
```

### Open in the browser

**<http://localhost:5500/>**

The page calls `http://127.0.0.1:8000/api/opportunities` automatically.

Alternative: double-click `index.html` (it opens as `file://`). That also works while the
backend is running, because CORS is enabled. The static-server URL is recommended because
it behaves like a normal web page.

API documentation: **<http://127.0.0.1:8000/docs>**

### Troubleshooting

| Symptom | Fix |
|---|---|
| "Could not load opportunities from the backend" | Check Terminal 1 is still running and open <http://127.0.0.1:8000/api/health>. Press **Retry connection**. |
| `python` opens Microsoft Store | Install Python 3.11+ and enable "Add python.exe to PATH". |
| `Activate.ps1 cannot be loaded` | Use the `.\.venv\Scripts\python.exe ...` commands above. |
| Port 8000 or 5500 already in use | Change the port in both the command and (for the API) `app.js`'s `API_BASE`; see section 9. |
| Verified only shows no cards | Expected. There are currently 0 verified records. |

## 8. Opportunity schema

Records live in `backend/app/data/opportunities.json`. The JSON field names are camelCase
so the browser can consume them directly.

| Field | Type | Meaning | Unknown looks like |
|---|---|---|---|
| `id` | string | Unique lowercase identifier | required |
| `name` | string | Opportunity name | required |
| `provider` | string | Organisation running it | required |
| `category` | string | `"Funding"`, `"Support"`, or `"Partnership"` | required |
| `description` | string | One or two plain sentences | required |
| `countries` | array | Countries covered, or `["ASEAN-wide"]` | empty array is invalid |
| `targetStages` | array or `null` | e.g. `["Seed"]`; `["Any"]` means all stages | `null` = unknown |
| `targetIndustries` | array or `null` | e.g. `["Fintech"]`; `["Any"]` means all industries | `null` = unknown |
| `goals` | array | Goals it may serve (may be empty) | `[]` |
| `eligibility` | array or `null` | Requirements as short strings | `null` = unknown; `[]` = none stated |
| `applicationDeadline` | string or `null` | `"YYYY-MM-DD"` | `null` = unknown |
| `deadlineNote` | string or `null` | Optional plain-language note | `null` |
| `dataStatus` | string | `"demo"` or `"verified"` | required |
| `sourceUrl` | string or `null` | Official URL; required when verified | `null` |
| `lastVerifiedDate` | string or `null` | `"YYYY-MM-DD"`; required when verified | `null` |
| `notes` | string | Why the record exists and caveats | optional |

### The rules that keep the data honest

1. **`null` means "we do not know".** It never means "not applicable".
2. **`"Any"` is different from `null`.** `["Any"]` is an explicit claim that a programme is
   open to everyone; `null` says we never established the target group.
3. **Never invent deadlines, eligibility, providers, or target groups.**
4. **A verified record needs evidence**: both `sourceUrl` and `lastVerifiedDate`.
5. **Verification is about the recorded information, not availability.**
6. **Demo records must not have a `sourceUrl`.** The validator flags this combination.

### How to add a record

1. Open `backend/app/data/opportunities.json` in any text editor.
2. Copy an existing object and give it a unique `id`.
3. Fill in only what you actually know; use `null` for everything else.
4. New fictional examples must use `"dataStatus": "demo"`, `"sourceUrl": null`,
   `"lastVerifiedDate": null`.
5. Real records must use `"dataStatus": "verified"` **and** include both evidence fields.
6. Save the file and reload the page. The **Data check** panel lists any mistakes. The
   backend also validates the file through Pydantic on startup/request.

Do not add a real programme until you have checked its official page yourself.

## 9. How matching works

The backend applies one fixed rule set (`rules-v1`) in
`backend/app/opportunity_matching.py`. The browser does **not** score records itself.

| Detail | Exact match | Wildcard | Unknown |
|---|---|---|---|
| Country | 3 points | `"ASEAN-wide"` = 2 | 0 |
| Industry | 2 points | `"Any"` = 1 | 0 (`null`) |
| Stage | 2 points | `"Any"` = 1 | 0 (`null`) |
| Goals | 1 point per shared goal (max 2) | — | 0 |

Maximum score is 9. The API returns both the raw score and `percent = round(score / 9 × 100)`.
Labels: **70%+ strong**, **40–69% possible**, **1–39% weak**, **0% no direct match**.

Ties are broken in favour of the more specific match (an exact country match appears before
an ASEAN-wide wildcard), then alphabetically.

**This is rule-based matching, not AI.** It never decides whether a startup is eligible and
never claims a programme is open. It ranks sample records using the four details entered in
the form and shows the exact reasons behind each rank. Verification status is **not** part of
the score.

### Changing the API location

`app.js` uses `http://127.0.0.1:8000` by default. Override it before `app.js` loads:

```html
<script>window.OPPORTUNITY_API_BASE = "http://127.0.0.1:9000";</script>
<script src="app.js"></script>
```

## 10. Demo vs verified records

- **Demo** — a fictional example. The card shows an amber "Demo data" badge and says there is
  nothing to apply to. Demo records have no `sourceUrl`.
- **Verified** — the recorded details were compared with the official source on
  `lastVerifiedDate`. The card shows a green "Verified" badge plus the date and a link.
- Filters let you view **all**, **verified only**, or **demo only** records, and the page
  always shows a count, e.g. `12 records: 0 verified, 12 demo.`
- A verified badge is **not** a claim that applications are open. Unknown deadlines say
  "Unknown — not recorded".
- Because no verified records exist yet, **Verified only** shows an explanatory empty state:
  "No verified opportunities have been added yet." It does not pretend the filter is broken.

## 11. API endpoints

Base URL: `http://127.0.0.1:8000`. Interactive docs: `/docs`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/opportunities` | All opportunity records (demo + verified) |
| GET | `/api/opportunities/{id}` | One record, or 404 |
| POST | `/api/opportunities/match` | Rank records for a startup profile |
| GET | `/api/projects` | Legacy: projects (filters: `q`, `domain`, `tech`, `experience`, `limit`) |
| GET | `/api/projects/{id}` | Legacy: one project |
| POST | `/api/projects` | Legacy: validated project submission, saved to JSON |
| GET | `/api/sponsors` | Legacy: sponsors |
| POST | `/api/match` | Legacy: sponsor matching for an inline project |
| POST | `/api/projects/{id}/match` | Legacy: sponsor matching for a stored project |
| GET | `/api/llm/status` | Active sponsor-matching mode and LLM config |

### Example: list opportunities (PowerShell)

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/opportunities"
```

### Example: match opportunities (PowerShell)

```powershell
$body = @{
  country  = "Malaysia"
  industry = "Fintech"
  stage    = "Seed"
  goals    = @("Funding")
  top_k    = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/opportunities/match" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Example response (trimmed):

```json
{
  "engine": "rules",
  "model": "rules-v1",
  "profile": {
    "country": "Malaysia",
    "industry": "Fintech",
    "stage": "Seed",
    "goals": ["Funding"],
    "top_k": 5
  },
  "matches": [
    {
      "opportunity": { "id": "demo-fund-02", "name": "AgriFood Innovation Fund - Demo Record", "...": "..." },
      "score": 6.0,
      "percent": 67,
      "label": "Possible match",
      "reasons": [
        "Covers your country (Malaysia).",
        "Intended for Seed companies.",
        "Matches your goal: Funding."
      ]
    }
  ],
  "summary": "Ranked 5 of 12 opportunities with fixed matching rules. Scores describe fit only, not eligibility.",
  "warning": null
}
```

`top_k` must be between 1 and 100 (default 50). The endpoint accepts an empty profile and
returns every record at 0%, which keeps the UI predictable.

### Example: submit a project (legacy, PowerShell)

```powershell
$project = @{
  title       = "Teh Tarik Trend Bot"
  description = "Analyses teh tarik price trends"
  team_name   = "Team Kopi"
  metrics     = @{
    tech_stack      = @("python")
    domains         = @("fintech")
    team_size       = 3
    experience_level = "beginner"
    open_source     = $true
    budget_usd      = 100
    duration_hours  = 24
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/projects" `
  -Method Post `
  -ContentType "application/json" `
  -Body $project
```

The project endpoint validates with Pydantic (invalid input returns **422**) and appends the
new record to `backend/app/data/projects.json`. It is a real submission endpoint.

**Opportunity records are read-only through the API.** There is intentionally no
opportunity-submission endpoint yet; records are curated in the JSON file so that demo and
verified data cannot be created accidentally through the UI.

## 12. Optional LLM configuration (legacy sponsor matcher only)

Opportunity matching is deterministic and **never calls an LLM**. The optional LLM applies
only to the original sponsor matcher (`POST /api/match`,
`POST /api/projects/{id}/match`).

```powershell
cd "C:\Users\60122\Documents\Hacktoberfest 2026\hack-teh-tarik\backend"
Copy-Item .env.example .env
notepad .env
```

Supported presets: `openrouter`, `groq`, `gemini`, `openai`, `ollama`, `custom`, `none`.
Relevant variables:

```dotenv
LLM_PRESET=openrouter
LLM_API_KEY=your-key-here
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
LLM_TIMEOUT=30
# LLM_BASE_URL=...   # required for preset=custom
```

- Secrets live only in `backend/.env`, which is git-ignored. Never put keys in `app.js`,
  `index.html`, or any tracked file.
- Without a key (or with `LLM_PRESET=none`) the sponsor matcher falls back to its local
  heuristic engine; everything else keeps working.
- Check the active mode at `GET /api/llm/status`.

## 13. Data check (built-in validation)

`validateOpportunities()` in `app.js` validates the records returned by the backend and flags:

- missing required text fields, duplicate ids, invalid categories
- invalid `YYYY-MM-DD` dates, including impossible dates and future verification dates
- verified records without `sourceUrl` or `lastVerifiedDate`
- demo records that have a `sourceUrl`
- malformed source URLs (must be full `http`/`https` URLs)

The result appears above the results list; details also go to the browser console. The
backend independently validates the same JSON with Pydantic. This is a data-quality check,
not a legal or factual verification.

## 14. Running the tests

```powershell
cd "C:\Users\60122\Documents\Hacktoberfest 2026\hack-teh-tarik\backend"
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The suite (27 tests) covers the opportunity list/lookup/match routes, scoring and tie-breaks,
the legacy project/sponsor endpoints, project-submission validation, and the heuristic
fallback. Tests are offline and restore `app/data/projects.json` after write tests.

## 15. Current dataset

- **12 demo records, 0 verified records.**
- All 12 are fictional and exist only to demonstrate matching and the interface.
- Eligibility is `null` on every demo record because inventing eligibility would be
  misleading, even in sample data.
- The separate legacy sponsor/project sample data is also illustrative, not confirmed.

## 16. Limitations and future improvements

### Current limitations

- All opportunities are fictional demo data; there is no live or verified source yet.
- Matching is simple rule-based logic, not machine learning or AI.
- No login, saved profile, database, or opportunity-submission endpoint.
- Deadline and eligibility are displayed, not evaluated; no automatic eligibility checking.
- No localisation, currency handling, or multilingual content.
- Not a substitute for official programme documentation.
- Records must be edited manually in `backend/app/data/opportunities.json`.
- The project was tested with Python 3.12 on Linux (WSL); the Windows commands above are the
  standard equivalents but should be smoke-tested once on the demo laptop.

### Future improvements

- Add verified records with official source URLs and verification dates (only after checking
  each page).
- Add a re-verification reminder workflow.
- Let users save or share a profile (still no account required).
- Add filtering by deadline and country groups.
- Translate the interface and opportunity descriptions into ASEAN languages.
- Add an authenticated admin endpoint for curated records, with audit logs.
- Replace the simple score with a documented, tested ranking model once real data exists.

## 17. License

MIT — see [`LICENSE`](LICENSE). Copyright (c) 2026 YC Wong. The license file is unchanged.

Project context: **Hacktoberfest KL 2026 only**.
