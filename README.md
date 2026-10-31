# ASEAN Opportunity Finder — Demo Prototype

A beginner-built prototype for the **Ecosystem Gateway / Hacktoberfest KL 2026** challenge.

> **Demo data only.** The 12 opportunity records in this repository are fictional examples
> written for the hackathon. They are **not** real programmes, providers, deadlines, or
> eligibility rules. Nothing here proves that any opportunity exists or is currently open.

---

## 1. The problem

ASEAN founders are often told that funding and support exist, but the details are scattered,
inconsistent, and rarely explain *why* a particular programme fits a particular startup.
Early-stage teams waste time on opportunities they were never eligible for, and they cannot
easily tell verified information from guesswork.

## 2. Who it is for

- First-time founders and student teams in ASEAN
- Very early teams (idea, pre-seed, seed) without advisers or networks
- Hackathon judges and mentors evaluating how matching could work

This is **not** an official directory and **not** financial or legal advice.

## 3. What it does

1. The user enters **country, industry, company stage, and goals** (all optional).
2. Each record gets a **transparent match score** with reasons in plain language.
3. Records show **deadline, eligibility, source URL, and verification status**, including
   explicit "Unknown" states instead of guesses.
4. Records can be filtered by **type** and **record status** (verified / demo), searched,
   and sorted.
5. A **data check** panel validates the file on every page load and reports problems.
6. The layout is responsive and needs no server.

## 4. Technology

- HTML5, CSS3, and vanilla JavaScript only
- No framework, no database, no package manager, no build step, no API keys
- Files load with plain `<script>` tags, so the page also works from `file://`

## 5. Files

```
hack-teh-tarik/
├─ index.html    Page: startup form, filters, results, data-check panel
├─ styles.css    Responsive styling
├─ data.js       The opportunity records and schema documentation
├─ app.js        Validation, matching, filtering, rendering
├─ README.md     This file
└─ LICENSE       MIT license (unchanged)
```

## 6. The opportunity schema

Every record in `data.js` is one object:

| Field | Type | Meaning | Unknown looks like |
|---|---|---|---|
| `id` | string | Unique, lowercase identifier | required |
| `name` | string | Opportunity name | required |
| `provider` | string | Organisation running it | required |
| `category` | string | `"Funding"`, `"Support"`, or `"Partnership"` | required |
| `description` | string | One or two plain sentences | required |
| `countries` | array | Countries covered, or `["ASEAN-wide"]` | `[]` is flagged by validation |
| `targetStages` | array or `null` | e.g. `["Seed"]`; `["Any"]` means all stages | `null` = unknown |
| `targetIndustries` | array or `null` | e.g. `["Fintech"]`; `["Any"]` means all industries | `null` = unknown |
| `goals` | array | Which user goals it may serve (may be empty) | `[]` |
| `eligibility` | array or `null` | Requirements as short strings | `null` = unknown; `[]` = none stated |
| `applicationDeadline` | string or `null` | `"YYYY-MM-DD"` | `null` = unknown |
| `deadlineNote` | string or `null` | Optional plain-language note | `null` |
| `dataStatus` | string | `"demo"` or `"verified"` | required |
| `sourceUrl` | string or `null` | Official URL; required when verified | `null` |
| `lastVerifiedDate` | string or `null` | `"YYYY-MM-DD"`; required when verified | `null` |
| `notes` | string | Why the record exists, caveats | required |

### The rules that keep the data honest

1. **`null` means "we do not know".** It never means "not applicable".
2. **`"Any"` is different from `null`.** `["Any"]` is an explicit claim that a programme is
   open to everyone; `null` says we never established the target group.
3. **Never invent deadlines, eligibility, providers, or target groups.**
4. **A verified record needs evidence**: both `sourceUrl` and `lastVerifiedDate`.
5. **Verification is about the recorded information, not availability.** A record verified
   last month may be closed today.
6. **Demo records must not have a `sourceUrl`.** The validator flags this combination.

## 7. How to add a record

1. Open `data.js` in any text editor (Notepad, VS Code, etc.).
2. Copy the template comment at the top of the file.
3. Paste a new object at the end of the `OPPORTUNITIES` array, before the closing `];`.
4. Give it a unique `id`, fill in what you actually know, and use `null` for everything else.
5. New fictional examples must use `dataStatus: "demo"`, `sourceUrl: null`,
   `lastVerifiedDate: null`.
6. Real records must use `dataStatus: "verified"` **and** include both evidence fields.
7. Save the file and refresh the browser. The **Data check** panel will list any mistakes.

Do not add a real programme until you have checked its official page yourself. The team will
add verified records only after collecting official source URLs.

## 8. How verification works

- **Demo** — a fictional example. The card shows an amber "Demo data" badge and says there is
  nothing to apply to.
- **Verified** — the recorded details were compared with the official source on
  `lastVerifiedDate`. The card shows a green "Verified" badge plus the date and a link.
- Filters let you view **all**, **verified only**, or **demo only** records, and the page
  always shows a count, e.g. `12 records: 0 verified, 12 demo.`
- A verified badge is **not** a claim that applications are open. The deadline field is
  always presented as "as recorded — check the official source", and unknown deadlines say
  "Unknown — not recorded".
- Because no verified records exist yet, choosing **Verified only** shows an explanatory
  empty state: "No verified opportunities have been added yet." It does not pretend the
  filter is broken.

The scoring system ignores `dataStatus`. Verification is transparency, not relevance.

## 9. How matching works

| Detail | Exact match | Wildcard |
|---|---|---|
| Country | 3 points | `"ASEAN-wide"` = 2 |
| Industry | 2 points | `"Any"` = 1 |
| Stage | 2 points | `"Any"` = 1 |
| Goals | 1 point per shared goal (max 2) | — |

Maximum score is 9; the card shows `score ÷ 9` as a percentage and explains every point.
`null` fields (unknown) earn 0 points rather than a guess. Labels: 70%+ strong, 40–69%
possible, 1–39% weak, 0% no direct match.

This is **rule-based matching, not AI**. It never decides whether a startup is eligible, and
it never claims a programme is open. It ranks sample records using the four details entered
in the form and shows the exact reasons behind each rank.

## 10. How to run on Windows 11 (no installation)

You do not need Python, Node.js, a terminal, or internet access.

1. Open File Explorer and go to the project folder.
2. **Double-click `index.html`**.
3. Edge, Chrome, or Firefox opens the prototype.
4. Choose your startup details and press **Find opportunities**.
5. Use **Type**, **Record status**, **Search**, and **Sort** to explore.
6. After editing `data.js`, save and press **F5** in the browser.

If double-clicking opens a code editor: right-click `index.html` → **Open with** → choose a
browser.

### A 2-minute demo script

1. Show the header: what it does, three steps, "Rule-based, not AI".
2. Pick **Malaysia**, **Fintech**, **Seed**, tick **Funding**, press **Find opportunities**.
3. Point out the match percentages and the reasons under each card.
4. Open **What to verify before applying** and the "Unknown — not recorded" deadline.
5. Set **Record status → Verified only** and read the explanatory empty state.
6. Show the green **Data check passed** panel above the results.
7. Read the demo-data banner and the "not AI" note aloud — honesty is part of the pitch.

## 11. Data check (built-in validation)

`validateOpportunities()` in `app.js` runs on every page load and flags:

- missing required text fields, duplicate ids, invalid categories
- invalid `YYYY-MM-DD` dates, including impossible dates and future verification dates
- verified records without `sourceUrl` or `lastVerifiedDate`
- demo records that have a `sourceUrl` (suspicious combination)
- malformed source URLs (must be full `http`/`https` URLs)

The result appears in a panel above the results list; details also go to the browser console.
This is a data-quality check, not a legal or factual verification.

## 12. Current dataset

- **12 demo records, 0 verified records.**
- All 12 are fictional and exist only to demonstrate matching and the interface.
- Eligibility is `null` on every demo record because inventing eligibility would be
  misleading, even in sample data.

## 13. Current limitations and future improvements

### Current limitations

- All opportunities are fictional demo data; there is no live or verified source yet.
- Matching is simple rule-based logic, not machine learning or AI.
- No login, saved profile, database, or data leaving the browser.
- Deadline and eligibility are displayed, not evaluated; no automatic eligibility checking.
- No localisation, currency handling, or multilingual content.
- Not a substitute for official programme documentation.
- Data must be edited manually in `data.js`; there is no admin interface.

### Future improvements

- Add verified records with official source URLs and verification dates (only when the team
  has checked each page).
- Add an "official source last checked" reminder workflow and periodic re-verification.
- Let users save or share a profile (still client-side, no account required).
- Add filtering by deadline and country groups.
- Translate the interface and opportunity descriptions into ASEAN languages.
- Replace the simple score with a documented, tested ranking model once real data exists.
- Add automated tests for validation, scoring, and filters.

## 14. Git and license

The repository is on the `main` branch. Useful commands (Git must be installed):

```powershell
git status
git diff
git add .
git commit -m "Add opportunity schema and verification states"
```

This work has **not** been committed or pushed. Decide as a team before committing.

MIT — see [`LICENSE`](LICENSE). Copyright (c) 2026 YC Wong.

Project context: **Hacktoberfest KL 2026 only**.
