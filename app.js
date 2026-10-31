/*
 * app.js
 * ==================================================================
 * The browser "brain" of the integrated prototype.
 *
 * Records come from the FastAPI backend:
 *   GET  /api/opportunities        -> all records (demo + verified)
 *   POST /api/opportunities/match  -> ranked matches + reasons
 *
 * It still does the presentation work locally:
 *   1. Validates the records received from the backend.
 *   2. Filters, searches, and sorts them.
 *   3. Draws the cards, badges, deadlines, sources, and match reasons.
 *
 * Matching itself is deterministic Python on the backend. There is no
 * AI-generated eligibility decision anywhere in this file.
 * ==================================================================
 */

// ---------- 1. Configuration and page elements ----------

/**
 * The backend runs on port 8000 by default. Override before this script if
 * your backend lives elsewhere:
 *   <script>window.OPPORTUNITY_API_BASE = "http://127.0.0.1:9000";</script>
 */
const API_BASE = (
  window.OPPORTUNITY_API_BASE ||
  (window.location.port === "8000" ? window.location.origin : "http://127.0.0.1:8000")
).replace(/\/+$/, "");

const formEl = document.getElementById("profile-form");
const countryEl = document.getElementById("country");
const industryEl = document.getElementById("industry");
const stageEl = document.getElementById("stage");
const typeFilterEl = document.getElementById("type-filter");
const statusFilterEl = document.getElementById("status-filter");
const searchEl = document.getElementById("search");
const sortEl = document.getElementById("sort");
const resultsEl = document.getElementById("results");
const summaryEl = document.getElementById("results-summary");
const countsEl = document.getElementById("data-counts");
const dataCheckEl = document.getElementById("data-check");
const formMessageEl = document.getElementById("form-message");
const sourceStatusEl = document.getElementById("source-status");
const submitButton = formEl.querySelector('button[type="submit"]');

const CATEGORIES = ["Funding", "Support", "Partnership"];
const ALLOWED_STATUSES = ["demo", "verified"];

// Highest possible score returned by the backend (country 3 + industry 2 +
// stage 2 + goals 2). Used only for display sanity checks.
const MAX_SCORE = 9;

/** Records loaded from the backend. Never replaced by hand-written demo data. */
let OPPORTUNITIES = [];
/** opportunity id -> match result from the backend. */
const MATCHES = new Map();
/** Profile last submitted successfully, or null in preview mode. */
let profile = null;
/** "loading" | "ready" | "error" */
let dataState = "loading";
let dataError = "";
let isMatching = false;

// ---------- 2. Small helpers ----------

/** Make text safe before putting it into HTML. */
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** True only for a real calendar date written as YYYY-MM-DD. */
function isValidIsoDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

/** "2026-10-31" -> "31 Oct 2026" (without relying on browser locale). */
function formatIsoDate(value) {
  if (!isValidIsoDate(value)) return String(value);
  const [year, month, day] = value.split("-").map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/** Today's date as YYYY-MM-DD, used to catch dates in the future. */
function todayIso() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function isWebUrl(value) {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

/** Turn null / [] / array into readable text. */
function listText(value) {
  if (value === null) return "Unknown";
  if (Array.isArray(value) && value.length === 0) return "None recorded";
  return value.join(", ");
}

function setSourceStatus(text, kind) {
  if (!sourceStatusEl) return;
  sourceStatusEl.textContent = text;
  sourceStatusEl.className = `source-status${kind ? ` source-status-${kind}` : ""}`;
}

function setFormMessage(message) {
  formMessageEl.textContent = message;
  formMessageEl.hidden = !message;
}

function setSubmitBusy(busy) {
  isMatching = busy;
  submitButton.disabled = busy;
  submitButton.textContent = busy ? "Matching…" : "Find opportunities";
  submitButton.setAttribute("aria-busy", String(busy));
}

// ---------- 3. API access ----------

/**
 * Fetch JSON with a timeout and a useful error message.
 * A failed request must never look like an empty or successful result.
 */
async function fetchJson(path, options = {}) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let detail = "";
      try {
        const body = await response.json();
        if (typeof body.detail === "string") {
          detail = `: ${body.detail}`;
        } else if (body.detail) {
          detail = `: ${JSON.stringify(body.detail)}`;
        }
      } catch {
        // The status code alone is still useful.
      }
      throw new Error(`HTTP ${response.status}${detail}`);
    }

    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("the request timed out after 10 seconds");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

// ---------- 4. Data validation ----------

/**
 * Check every record for obvious mistakes.
 *
 * Returns { recordCount, issues: [ "message", ... ] }.
 * The same rules are enforced by the backend Pydantic model; this check keeps
 * the visible feedback from the original prototype.
 */
function validateOpportunities(records) {
  const issues = [];
  const seenIds = new Set();
  const today = todayIso();

  if (!Array.isArray(records)) {
    return { recordCount: 0, issues: ["The backend response was not a list of records."] };
  }

  records.forEach((record, index) => {
    const label = `Record ${index + 1}${record && record.id ? ` ("${record.id}")` : ""}`;

    if (!record || typeof record !== "object") {
      issues.push(`${label}: is not an object.`);
      return;
    }

    // Required text fields.
    ["id", "name", "provider", "description"].forEach((field) => {
      if (typeof record[field] !== "string" || record[field].trim() === "") {
        issues.push(`${label}: "${field}" must be a non-empty string.`);
      }
    });

    // Unique id.
    if (typeof record.id === "string" && record.id.trim() !== "") {
      if (seenIds.has(record.id)) {
        issues.push(`${label}: duplicate id "${record.id}".`);
      }
      seenIds.add(record.id);
    }

    // Category.
    if (!CATEGORIES.includes(record.category)) {
      issues.push(`${label}: category must be one of ${CATEGORIES.join(", ")}.`);
    }

    // Countries.
    if (!Array.isArray(record.countries) || record.countries.length === 0) {
      issues.push(`${label}: countries must be a non-empty array (use ["ASEAN-wide"] if needed).`);
    }

    // Target lists: null (unknown) or a non-empty array.
    ["targetStages", "targetIndustries"].forEach((field) => {
      const value = record[field];
      if (value !== null && (!Array.isArray(value) || value.length === 0)) {
        issues.push(`${label}: "${field}" must be null or a non-empty array.`);
      }
    });

    // Goals may be empty, but must be an array.
    if (!Array.isArray(record.goals)) {
      issues.push(`${label}: "goals" must be an array (it may be empty).`);
    }

    // Eligibility: null (unknown) or an array (empty = none recorded).
    if (record.eligibility !== null && !Array.isArray(record.eligibility)) {
      issues.push(`${label}: "eligibility" must be null or an array.`);
    }

    // Deadline.
    if (record.applicationDeadline !== null && !isValidIsoDate(record.applicationDeadline)) {
      issues.push(`${label}: applicationDeadline must be null or a valid YYYY-MM-DD date.`);
    }

    // Status.
    if (!ALLOWED_STATUSES.includes(record.dataStatus)) {
      issues.push(`${label}: dataStatus must be "demo" or "verified".`);
    }

    // Source URL.
    if (record.sourceUrl !== null && !isWebUrl(record.sourceUrl)) {
      issues.push(`${label}: sourceUrl must be null or a full http(s) URL.`);
    }

    // Last verified date.
    if (record.lastVerifiedDate !== null) {
      if (!isValidIsoDate(record.lastVerifiedDate)) {
        issues.push(`${label}: lastVerifiedDate must be null or a valid YYYY-MM-DD date.`);
      } else if (record.lastVerifiedDate > today) {
        issues.push(`${label}: lastVerifiedDate is in the future (${record.lastVerifiedDate}).`);
      }
    }

    // The rule that matters most: verified records need evidence.
    if (record.dataStatus === "verified") {
      if (record.sourceUrl === null) {
        issues.push(`${label}: verified records must include an official sourceUrl.`);
      }
      if (record.lastVerifiedDate === null) {
        issues.push(`${label}: verified records must include lastVerifiedDate.`);
      }
    }

    // Suspicious combination: demo data pointing at a real source.
    if (record.dataStatus === "demo" && record.sourceUrl !== null) {
      issues.push(
        `${label}: a demo record has a sourceUrl. Either mark it verified with a date, or remove the URL.`
      );
    }
  });

  return { recordCount: records.length, issues };
}

function renderDataCheckPending() {
  dataCheckEl.className = "data-check data-check-pending";
  dataCheckEl.textContent = "Waiting for opportunity data from the local backend…";
}

function renderDataCheckError(message) {
  dataCheckEl.className = "data-check data-check-error";
  dataCheckEl.innerHTML =
    "<strong>Data check not run.</strong> " +
    `${escapeHtml(message)} The page will not show records until the backend is reachable.`;
}

function renderDataCheck() {
  const result = validateOpportunities(OPPORTUNITIES);

  if (result.issues.length === 0) {
    dataCheckEl.className = "data-check";
    dataCheckEl.innerHTML =
      `<strong>Data check passed.</strong> ${result.recordCount} records checked: ` +
      "required fields, date formats, and verification rules are valid.";
  } else {
    dataCheckEl.className = "data-check data-check-error";
    dataCheckEl.innerHTML =
      `<strong>Data check found ${result.issues.length} issue(s).</strong>` +
      `<ul>${result.issues.map((issue) => `<li>${escapeHtml(issue)}</li>`).join("")}</ul>` +
      "<p>Fix the JSON in <code>backend/app/data/opportunities.json</code>, then reload this page.</p>";
  }

  // Also log details for anyone with developer tools open.
  if (result.issues.length > 0) {
    console.warn("Data check issues:", result.issues);
  }
}

// ---------- 5. Card pieces ----------

function typeClass(category) {
  if (category === "Funding") return "badge-funding";
  if (category === "Support") return "badge-support";
  return "badge-partner";
}

function statusBadge(record) {
  if (record.dataStatus === "verified") {
    return '<span class="badge badge-verified">Verified</span>';
  }
  return '<span class="badge badge-demo">Demo data</span>';
}

/** The deadline must never look like "open now". */
function deadlineHtml(record) {
  const note = record.deadlineNote ? ` ${escapeHtml(record.deadlineNote)}` : "";

  if (record.applicationDeadline !== null) {
    return `
      <p class="deadline">
        <strong>Application deadline:</strong>
        <time datetime="${escapeHtml(record.applicationDeadline)}">${formatIsoDate(
      record.applicationDeadline
    )}</time>
        <span class="muted">as recorded - check the official source for changes.</span>${note}
      </p>`;
  }

  const demoNote =
    record.dataStatus === "demo" ? " This demo record has no real deadline." : "";
  return `
    <p class="deadline">
      <strong>Application deadline:</strong> Unknown - not recorded.${note}${demoNote}
    </p>`;
}

function eligibilityHtml(record) {
  if (record.eligibility === null) {
    return `
      <div class="info-block">
        <h4>Eligibility</h4>
        <p>Unknown - not recorded. Check the programme's own rules before applying.</p>
      </div>`;
  }

  if (record.eligibility.length === 0) {
    return `
      <div class="info-block">
        <h4>Eligibility</h4>
        <p>No specific requirements recorded.</p>
      </div>`;
  }

  return `
    <div class="info-block">
      <h4>Eligibility</h4>
      <ul>${record.eligibility.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>`;
}

function sourceHtml(record) {
  if (record.sourceUrl !== null) {
    return `
      <p class="source">
        <a href="${escapeHtml(record.sourceUrl)}" target="_blank" rel="noopener noreferrer">
          Official source
        </a>
        <span class="muted">(opens in a new tab)</span>
      </p>`;
  }
  return '<p class="source muted">No official source recorded.</p>';
}

function verificationHtml(record) {
  if (record.lastVerifiedDate !== null) {
    return `
      <p class="verified-date">
        Information last verified: <time datetime="${escapeHtml(record.lastVerifiedDate)}">${
      formatIsoDate(record.lastVerifiedDate)
    }</time>.
        This covers the recorded details only, not current availability.
      </p>`;
  }
  return '<p class="verified-date muted">Not verified against a source.</p>';
}

/** Honest checklist generated from what the record does and does not contain. */
function checklistItems(record) {
  const items = [];

  if (record.dataStatus === "demo") {
    items.push("This record is fictional - there is nothing to apply to.");
  }
  if (record.sourceUrl === null) {
    items.push("No official source is recorded, so the details cannot be confirmed.");
  }
  if (record.eligibility === null) {
    items.push("Eligibility is not recorded - check the programme's own eligibility rules.");
  }
  if (record.applicationDeadline === null) {
    items.push("The application deadline is not recorded - check the official page.");
  }

  items.push("Confirm the programme exists and is currently accepting applications.");
  items.push("Check fees, data handling, and any legal or regulatory requirements.");
  return items;
}

function matchBlockHtml(match) {
  if (!match) {
    return `
      <div class="match">
        <p class="preview-note">
          Preview only - fill in your startup details and press
          &ldquo;Find opportunities&rdquo; to see a rule-based score and reasons.
        </p>
      </div>`;
  }

  const percent = Math.max(0, Math.min(100, Number(match.percent) || 0));
  const reasons = Array.isArray(match.reasons) ? match.reasons : [];

  return `
    <div class="match">
      <div class="match-head">
        <span class="match-label">${escapeHtml(match.label || "Match")}</span>
        <span class="match-percent">${percent}%</span>
      </div>
      <div class="meter" role="img" aria-label="Match strength: ${percent} percent">
        <span style="width: ${percent}%"></span>
      </div>
      <h4>Why this may be relevant</h4>
      <ul class="reasons">
        ${reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
      </ul>
      <p class="match-source">Rule-based score from the local backend - not an eligibility decision.</p>
    </div>`;
}

function cardHtml(record, match) {
  const fineprint =
    record.dataStatus === "demo"
      ? "Fictional demo record. Not a real programme and not evidence that funding or support is available."
      : `Verified record: details checked on ${formatIsoDate(
          record.lastVerifiedDate
        )}. Availability may change; always confirm on the official source.`;

  return `
    <article class="card">
      <div class="card-top">
        <span class="badge ${typeClass(record.category)}">${escapeHtml(record.category)}</span>
        ${statusBadge(record)}
      </div>

      <h3>${escapeHtml(record.name)}</h3>
      <p class="provider">${escapeHtml(record.provider)}</p>
      <p class="summary">${escapeHtml(record.description)}</p>

      <p class="card-meta">
        <span><strong>Countries:</strong> ${escapeHtml(listText(record.countries))}</span>
        <span><strong>Stages:</strong> ${escapeHtml(listText(record.targetStages))}</span>
        <span><strong>Industries:</strong> ${escapeHtml(listText(record.targetIndustries))}</span>
        <span><strong>Goals:</strong> ${escapeHtml(listText(record.goals))}</span>
      </p>

      ${matchBlockHtml(match)}

      ${deadlineHtml(record)}
      ${eligibilityHtml(record)}

      <details class="verify">
        <summary>What to verify before applying</summary>
        <ul>${checklistItems(record)
          .map((item) => `<li>${escapeHtml(item)}</li>`)
          .join("")}</ul>
      </details>

      <div class="record-footer">
        ${sourceHtml(record)}
        ${verificationHtml(record)}
      </div>

      <p class="fineprint">${escapeHtml(fineprint)}</p>
    </article>
  `;
}

function emptyHtml() {
  if (statusFilterEl.value === "verified") {
    const demoCount = OPPORTUNITIES.filter((record) => record.dataStatus === "demo").length;
    return `
      <p class="empty">
        <strong>No verified opportunities have been added yet.</strong>
        All ${demoCount} current records are clearly labelled demo data. A record appears here
        only after an official source URL and a verification date are added. Switch to
        &ldquo;All records&rdquo; or &ldquo;Demo only&rdquo; to explore the demo set.
      </p>
    `;
  }

  if (OPPORTUNITIES.length === 0) {
    return `
      <p class="empty">
        <strong>The backend returned no opportunity records.</strong>
        Add records to <code>backend/app/data/opportunities.json</code> and reload this page.
      </p>
    `;
  }

  return `
    <p class="empty">
      No records match these filters. Try clearing the search box, choosing
      &ldquo;All types&rdquo;, or switching the record status back to &ldquo;All records&rdquo;.
    </p>
  `;
}

function loadingHtml() {
  return `
    <div class="loading" role="status">
      <span class="spinner" aria-hidden="true"></span>
      <p><strong>Loading opportunities…</strong></p>
      <p class="muted">Reading records from ${escapeHtml(API_BASE)}/api/opportunities</p>
    </div>
  `;
}

function apiErrorHtml(message) {
  return `
    <div class="api-error" role="alert">
      <h3>Could not load opportunities from the backend</h3>
      <p><strong>What happened:</strong> ${escapeHtml(message)}</p>
      <p>
        The page will not show sample or stale records, because that would hide the problem.
        Start the backend, then retry.
      </p>
      <p class="api-error-cmd">
        From the repository root:<br />
        <code>cd backend</code><br />
        <code>python -m uvicorn app.main:app --reload</code>
      </p>
      <p class="muted">
        Expected API: <code>${escapeHtml(API_BASE)}/api/opportunities</code> ·
        <a href="${escapeHtml(API_BASE)}/docs" target="_blank" rel="noopener noreferrer">API docs</a>
      </p>
      <button type="button" class="btn btn-primary" data-action="retry-load">Retry connection</button>
    </div>
  `;
}

// ---------- 6. Filter, sort, render ----------

function updateCounts() {
  const demoCount = OPPORTUNITIES.filter((record) => record.dataStatus === "demo").length;
  const verifiedCount = OPPORTUNITIES.filter((record) => record.dataStatus === "verified").length;
  countsEl.textContent = `${OPPORTUNITIES.length} records: ${verifiedCount} verified, ${demoCount} demo.`;
}

function applyFilters() {
  if (dataState !== "ready") return;

  const selectedType = typeFilterEl.value;
  const selectedStatus = statusFilterEl.value;
  const query = searchEl.value.trim().toLowerCase();
  const sortMode = sortEl.value;

  let items = OPPORTUNITIES.map((record) => ({
    record,
    match: profile ? MATCHES.get(record.id) || null : null,
  }));

  if (selectedType) {
    items = items.filter((item) => item.record.category === selectedType);
  }

  if (selectedStatus) {
    items = items.filter((item) => item.record.dataStatus === selectedStatus);
  }

  if (query) {
    items = items.filter((item) => {
      const record = item.record;
      const haystack = [
        record.name,
        record.provider,
        record.category,
        record.description,
        record.countries.join(" "),
        record.targetStages === null ? "" : record.targetStages.join(" "),
        record.targetIndustries === null ? "" : record.targetIndustries.join(" "),
        record.goals.join(" "),
        record.eligibility === null ? "" : record.eligibility.join(" "),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }

  if (sortMode === "match" && profile) {
    items.sort(
      (a, b) =>
        (b.match ? b.match.percent : 0) - (a.match ? a.match.percent : 0) ||
        a.record.name.localeCompare(b.record.name)
    );
  } else {
    items.sort((a, b) => a.record.name.localeCompare(b.record.name));
  }

  const total = OPPORTUNITIES.length;
  summaryEl.textContent = profile
    ? `Showing ${items.length} of ${total} records, ranked by the backend for your profile.`
    : `Preview mode: showing ${items.length} of ${total} records. Fill in the form and press "Find opportunities" to see ranked matches.`;

  resultsEl.innerHTML =
    items.length === 0
      ? emptyHtml()
      : items.map((item) => cardHtml(item.record, item.match)).join("");
}

// ---------- 7. Load records from the backend ----------

async function loadOpportunities() {
  dataState = "loading";
  dataError = "";
  OPPORTUNITIES = [];
  MATCHES.clear();
  profile = null;

  countsEl.textContent = "";
  summaryEl.textContent = "Loading opportunity records from the local backend…";
  resultsEl.innerHTML = loadingHtml();
  renderDataCheckPending();
  setSourceStatus(`Connecting to ${API_BASE}…`, "loading");
  setSubmitBusy(false);

  try {
    const records = await fetchJson("/api/opportunities");
    if (!Array.isArray(records)) {
      throw new Error("the backend response was not a list of records");
    }

    OPPORTUNITIES = records;
    dataState = "ready";
    renderDataCheck();
    updateCounts();
    setSourceStatus(
      `Connected to the local backend · ${records.length} record(s) from /api/opportunities`,
      "ready"
    );
    applyFilters();
  } catch (error) {
    dataState = "error";
    dataError = error.message || String(error);
    OPPORTUNITIES = [];
    countsEl.textContent = "";
    summaryEl.textContent = "Opportunities could not be loaded. See the error below.";
    renderDataCheckError(`Could not read ${API_BASE}/api/opportunities (${dataError}).`);
    setSourceStatus(`Backend unavailable · ${API_BASE}`, "error");
    resultsEl.innerHTML = apiErrorHtml(dataError);
    console.error("Opportunity load failed:", error);
  }
}

// ---------- 8. Events ----------

function readProfile() {
  const checkedGoals = formEl.querySelectorAll('input[name="goals"]:checked');
  return {
    country: countryEl.value,
    industry: industryEl.value,
    stage: stageEl.value,
    goals: Array.from(checkedGoals).map((checkbox) => checkbox.value),
  };
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isMatching) return;

  const candidate = readProfile();
  const hasAnyDetail =
    candidate.country ||
    candidate.industry ||
    candidate.stage ||
    candidate.goals.length > 0;

  if (!hasAnyDetail) {
    setFormMessage(
      "Please choose at least one detail - country, industry, stage, or a goal - so we can explain the matches."
    );
    return;
  }

  if (dataState !== "ready") {
    setFormMessage(
      "Opportunities are not loaded yet. Start the backend and press Retry connection before matching."
    );
    return;
  }

  setFormMessage("");
  setSubmitBusy(true);
  summaryEl.textContent = "Scoring opportunities on the local backend…";

  try {
    const data = await fetchJson("/api/opportunities/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...candidate, top_k: 50 }),
    });

    if (!data || !Array.isArray(data.matches)) {
      throw new Error("the backend response did not include a matches list");
    }

    MATCHES.clear();
    data.matches.forEach((match) => {
      if (match && match.opportunity && match.opportunity.id) {
        MATCHES.set(match.opportunity.id, match);
      }
    });
    profile = candidate;
    applyFilters();

    if (window.innerWidth < 900) {
      document.getElementById("results-heading").scrollIntoView({ behavior: "smooth" });
    }
  } catch (error) {
    // Keep any previous successful results visible; make the failure loud.
    setFormMessage(
      `Could not get matches from the backend (${error.message}). ` +
        "Check that the backend is still running, then try again."
    );
    summaryEl.textContent = profile
      ? "Showing the previous successful match results. The latest request failed."
      : "Matching failed. See the message above the form.";
    console.error("Matching request failed:", error);
  } finally {
    setSubmitBusy(false);
  }
});

[typeFilterEl, statusFilterEl, searchEl, sortEl].forEach((element) => {
  element.addEventListener("input", applyFilters);
  element.addEventListener("change", applyFilters);
});

// "reset" fires before the fields are cleared, so wait one tick.
formEl.addEventListener("reset", () => {
  window.setTimeout(() => {
    profile = null;
    MATCHES.clear();
    setFormMessage("");
    applyFilters();
  }, 0);
});

resultsEl.addEventListener("click", (event) => {
  const retry = event.target.closest('[data-action="retry-load"]');
  if (retry) loadOpportunities();
});

// ---------- 9. First render ----------

/**
 * Browsers can restore form values when using back/forward, which would leave
 * the fields filled in while the results show preview mode. Reset the form and
 * reload the records in that case so a live demo always starts consistently.
 */
window.addEventListener("pageshow", (event) => {
  if (!event.persisted) return;
  formEl.reset();
  profile = null;
  MATCHES.clear();
  setFormMessage("");
  loadOpportunities();
});

loadOpportunities();

// Make helpers available to a console or a future test page.
window.validateOpportunities = validateOpportunities;
window.renderDataCheck = renderDataCheck;
window.loadOpportunities = loadOpportunities;
window.API_BASE = API_BASE;

// Reference MAX_SCORE so a future refactor cannot silently remove it.
window.OPPORTUNITY_MAX_SCORE = MAX_SCORE;
