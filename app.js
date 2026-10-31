/*
 * app.js
 * ==================================================================
 * Browser logic for the dual-sided ASEAN Opportunity Gateway.
 *
 * Records and scores come from the FastAPI backend:
 *   GET  /api/opportunities        -> startup support opportunities
 *   POST /api/opportunities/match  -> ranked opportunities + reasons
 *   GET  /api/startups             -> illustrative startup profiles
 *   POST /api/startups/match       -> ranked startup profiles + reasons
 *
 * Matching is deterministic Python on the backend. This file only:
 *   1. Validates the records it receives.
 *   2. Keeps the two role-specific forms and result sets separate.
 *   3. Draws cards, badges, scores, missing-information notes, and states.
 *
 * It never invents results and never claims that a contact, application,
 * or introduction has happened.
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

const $ = (id) => document.getElementById(id);

const workspaceEl = $("workspace");
const startupPanel = $("startup-panel");
const investorPanel = $("investor-panel");
const startupForm = $("startup-form");
const investorForm = $("investor-form");
const startupHeading = $("startup-form-heading");
const investorHeading = $("investor-form-heading");
const roleInputs = Array.from(document.querySelectorAll('input[name="role"]'));
const roleStatusEl = $("role-status");

const resultsHeadingEl = $("results-heading");
const resultsEl = $("results");
const summaryEl = $("results-summary");
const countsEl = $("data-counts");
const sourceStatusEl = $("source-status");
const noticeEl = $("results-notice");
const explainerEl = $("matching-explainer");
const dataCheckEl = $("data-check");
const sortEl = $("sort");
const verifiedOnlyEl = $("verified-only");

const startupDescriptionEl = $("startup-description");
const startupDescriptionCountEl = $("startup-description-count");
const investorDescriptionEl = $("investor-description");
const investorDescriptionCountEl = $("investor-description-count");

const ROLE_CONFIG = {
  startup: {
    label: "Startup Owner",
    resultsTitle: "Your Matched Opportunities",
    dataKey: "opportunities",
    noun: "opportunities",
    endpoint: "/api/opportunities/match",
    listEndpoint: "/api/opportunities",
    dataFile: "backend/app/data/opportunities.json",
    action: "Find Opportunities",
    busyText: "Finding opportunities…",
    loadingText: "Scoring opportunities with the rule-based backend…",
    previewNote:
      "Preview only — complete the startup profile and press “Find Opportunities” to see a rule-based score and reasons.",
    explainer: `
      <p>
        <strong>Rule-based, not AI.</strong> The Python backend scores each opportunity on
        country coverage (3 points), industry focus (2), startup stage (2), and shared goals
        (2), for a maximum of 9. The percentage is that score out of 9. Verification status
        is never part of the score.
      </p>
      <p>
        Your funding amount and short description are sent for context but are not scored,
        because these demo opportunity records do not publish funding ranges.
      </p>`,
  },
  investor: {
    label: "Investor",
    resultsTitle: "Startups Matching Your Investment Thesis",
    dataKey: "startups",
    noun: "startup profiles",
    endpoint: "/api/startups/match",
    listEndpoint: "/api/startups",
    dataFile: "backend/app/data/startups.json",
    action: "Find Matching Startups",
    busyText: "Matching startups…",
    loadingText: "Scoring startup profiles with the rule-based backend…",
    previewNote:
      "Preview only — complete the investment thesis and press “Find Matching Startups” to see rule-based scores and reasons.",
    explainer: `
      <p>
        <strong>Rule-based, not AI.</strong> The Python backend scores each startup on
        geography (30 points), industry (25), stage (20), investment strategy (15), and
        ticket-size compatibility (10). Only criteria with enough information on both sides
        are assessed, and the score is normalised over those criteria — so missing data is
        explained rather than penalised. Verification status is never scored.
      </p>
      <p>
        A high score is a fit signal only. It is not an investment recommendation, offer,
        eligibility decision, or introduction.
      </p>`,
  },
};

const ALLOWED_STATUSES = ["demo", "verified"];
const ALLOWED_CURRENCIES = ["USD", "SGD", "MYR"];
const OPPORTUNITY_CATEGORIES = ["Funding", "Support", "Partnership"];
const STARTUP_INDUSTRIES = [
  "Fintech",
  "Artificial Intelligence",
  "Software / SaaS",
  "Climate / Clean Energy",
  "Healthcare",
  "Education",
  "Agriculture / Food",
  "E-commerce / Retail",
  "Logistics / Mobility",
  "Manufacturing",
  "Other",
];
const INVESTOR_STRATEGIES = [
  "Early-stage growth",
  "Revenue-generating businesses",
  "Deep technology",
  "Impact / ESG",
  "Strategic partnerships",
  "Market expansion",
  "Other",
];

// ---------- 2. State ----------

/** Backend records, loaded once per page load. */
const DATA = { opportunities: [], startups: [] };
/** role -> Map(record id -> backend match result) */
const MATCHES = { startup: new Map(), investor: new Map() };
/** role -> the profile that produced the matches, or null for preview mode. */
const PROFILES = { startup: null, investor: null };
/** role -> full backend response (summary, warning, criteria). */
const RESPONSE_INFO = { startup: null, investor: null };
/** role -> last submitted profile, used by the retry button. */
const LAST_PAYLOAD = { startup: null, investor: null };

let role = null; // "startup" | "investor" | null
let loadState = "loading"; // "loading" | "ready" | "error"
let loadError = "";
let isBusy = false;

// ---------- 3. Small helpers ----------

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

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

function formatIsoDate(value) {
  if (!isValidIsoDate(value)) return String(value);
  const [year, month, day] = value.split("-").map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

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

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

/** null / [] / array -> readable text for opportunity fields. */
function listText(value) {
  if (value === null) return "Unknown";
  if (Array.isArray(value) && value.length === 0) return "None recorded";
  return value.join(", ");
}

function formatMoney(amount, currency) {
  const number = Number(amount);
  if (!Number.isFinite(number)) return "Unknown";
  return `${currency} ${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(number)}`;
}

function fundingText(startup) {
  if (startup.fundingSought === null || startup.fundingCurrency === null) {
    return '<span class="unknown">Not recorded</span>';
  }
  return escapeHtml(formatMoney(startup.fundingSought, startup.fundingCurrency));
}

function valueOrUnknown(value) {
  if (!isNonEmptyString(value)) return '<span class="unknown">Not recorded</span>';
  return escapeHtml(value);
}

function setFormMessage(which, message) {
  const element = $(`${which}-form-message`);
  if (!element) return;
  element.textContent = message;
  element.hidden = !message;
}

function setSourceStatus(text, kind) {
  sourceStatusEl.textContent = text;
  sourceStatusEl.className = `source-status${kind ? ` source-status-${kind}` : ""}`;
}

function setNotice(html) {
  if (!html) {
    noticeEl.hidden = true;
    noticeEl.innerHTML = "";
    return;
  }
  noticeEl.hidden = false;
  noticeEl.innerHTML = html;
}

function setBusy(which, busy) {
  const form = which === "startup" ? startupForm : investorForm;
  const config = ROLE_CONFIG[which];
  const button = form.querySelector('button[type="submit"]');
  button.disabled = busy;
  button.textContent = busy ? config.busyText : config.action;
  button.setAttribute("aria-busy", String(busy));
}

function readChecked(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(
    (input) => input.value
  );
}

// ---------- 4. API access ----------

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
          detail = `: ${JSON.stringify(body.detail).slice(0, 300)}`;
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

// ---------- 5. Data validation ----------

function validateOpportunities(records) {
  const issues = [];
  const seenIds = new Set();
  const today = todayIso();

  if (!Array.isArray(records)) {
    return { recordCount: 0, issues: ["The opportunity response was not a list of records."] };
  }

  records.forEach((record, index) => {
    const label = `Opportunity ${index + 1}${record && record.id ? ` ("${record.id}")` : ""}`;

    if (!record || typeof record !== "object") {
      issues.push(`${label}: is not an object.`);
      return;
    }

    ["id", "name", "provider", "description"].forEach((field) => {
      if (!isNonEmptyString(record[field])) {
        issues.push(`${label}: "${field}" must be a non-empty string.`);
      }
    });

    if (isNonEmptyString(record.id)) {
      if (seenIds.has(record.id)) issues.push(`${label}: duplicate id "${record.id}".`);
      seenIds.add(record.id);
    }

    if (!OPPORTUNITY_CATEGORIES.includes(record.category)) {
      issues.push(`${label}: category must be one of ${OPPORTUNITY_CATEGORIES.join(", ")}.`);
    }

    if (!Array.isArray(record.countries) || record.countries.length === 0) {
      issues.push(`${label}: countries must be a non-empty array (use ["ASEAN-wide"] if needed).`);
    }

    ["targetStages", "targetIndustries"].forEach((field) => {
      const value = record[field];
      if (value !== null && (!Array.isArray(value) || value.length === 0)) {
        issues.push(`${label}: "${field}" must be null or a non-empty array.`);
      }
    });

    if (!Array.isArray(record.goals)) {
      issues.push(`${label}: "goals" must be an array (it may be empty).`);
    }

    if (record.eligibility !== null && !Array.isArray(record.eligibility)) {
      issues.push(`${label}: "eligibility" must be null or an array.`);
    }

    if (record.applicationDeadline !== null && !isValidIsoDate(record.applicationDeadline)) {
      issues.push(`${label}: applicationDeadline must be null or a valid YYYY-MM-DD date.`);
    }

    if (!ALLOWED_STATUSES.includes(record.dataStatus)) {
      issues.push(`${label}: dataStatus must be "demo" or "verified".`);
    }

    if (record.sourceUrl !== null && !isWebUrl(record.sourceUrl)) {
      issues.push(`${label}: sourceUrl must be null or a full http(s) URL.`);
    }

    if (record.lastVerifiedDate !== null) {
      if (!isValidIsoDate(record.lastVerifiedDate)) {
        issues.push(`${label}: lastVerifiedDate must be null or a valid YYYY-MM-DD date.`);
      } else if (record.lastVerifiedDate > today) {
        issues.push(`${label}: lastVerifiedDate is in the future (${record.lastVerifiedDate}).`);
      }
    }

    if (record.dataStatus === "verified") {
      if (record.sourceUrl === null) {
        issues.push(`${label}: verified records must include an official sourceUrl.`);
      }
      if (record.lastVerifiedDate === null) {
        issues.push(`${label}: verified records must include lastVerifiedDate.`);
      }
    }

    if (record.dataStatus === "demo" && record.sourceUrl !== null) {
      issues.push(
        `${label}: a demo record has a sourceUrl. Either mark it verified with a date, or remove the URL.`
      );
    }
  });

  return { recordCount: records.length, issues };
}

function validateStartups(records) {
  const issues = [];
  const seenIds = new Set();
  const today = todayIso();

  if (!Array.isArray(records)) {
    return { recordCount: 0, issues: ["The startup response was not a list of records."] };
  }

  records.forEach((record, index) => {
    const label = `Startup ${index + 1}${record && record.id ? ` ("${record.id}")` : ""}`;

    if (!record || typeof record !== "object") {
      issues.push(`${label}: is not an object.`);
      return;
    }

    ["id", "name", "description", "country", "industry", "stage"].forEach((field) => {
      if (!isNonEmptyString(record[field])) {
        issues.push(`${label}: "${field}" must be a non-empty string.`);
      }
    });

    if (isNonEmptyString(record.id)) {
      if (seenIds.has(record.id)) issues.push(`${label}: duplicate id "${record.id}".`);
      seenIds.add(record.id);
    }

    if (isNonEmptyString(record.industry) && !STARTUP_INDUSTRIES.includes(record.industry)) {
      issues.push(`${label}: industry "${record.industry}" is outside the shared taxonomy.`);
    }

    if (!ALLOWED_STATUSES.includes(record.dataStatus)) {
      issues.push(`${label}: dataStatus must be "demo" or "verified".`);
    }

    if (record.revenueStatus !== null && !["Pre-revenue", "Revenue-generating"].includes(record.revenueStatus)) {
      issues.push(`${label}: revenueStatus must be null, "Pre-revenue", or "Revenue-generating".`);
    }

    if (
      record.fundingSought !== null &&
      (typeof record.fundingSought !== "number" || record.fundingSought < 0)
    ) {
      issues.push(`${label}: fundingSought must be null or a number of 0 or more.`);
    }

    if (record.fundingCurrency !== null && !ALLOWED_CURRENCIES.includes(record.fundingCurrency)) {
      issues.push(`${label}: fundingCurrency must be null or one of ${ALLOWED_CURRENCIES.join(", ")}.`);
    }

    if ((record.fundingSought === null) !== (record.fundingCurrency === null)) {
      issues.push(`${label}: fundingSought and fundingCurrency must both be set or both be null.`);
    }

    if (
      record.strategyTags !== null &&
      (!Array.isArray(record.strategyTags) ||
        record.strategyTags.length === 0 ||
        record.strategyTags.some((tag) => !INVESTOR_STRATEGIES.includes(tag)))
    ) {
      issues.push(
        `${label}: strategyTags must be null or a non-empty list of known strategy labels.`
      );
    }

    if (record.sourceUrl !== null && !isWebUrl(record.sourceUrl)) {
      issues.push(`${label}: sourceUrl must be null or a full http(s) URL.`);
    }

    if (record.lastVerifiedDate !== null) {
      if (!isValidIsoDate(record.lastVerifiedDate)) {
        issues.push(`${label}: lastVerifiedDate must be null or a valid YYYY-MM-DD date.`);
      } else if (record.lastVerifiedDate > today) {
        issues.push(`${label}: lastVerifiedDate is in the future (${record.lastVerifiedDate}).`);
      }
    }

    if (record.dataStatus === "verified") {
      if (record.sourceUrl === null) {
        issues.push(`${label}: verified records must include an official sourceUrl.`);
      }
      if (record.lastVerifiedDate === null) {
        issues.push(`${label}: verified records must include lastVerifiedDate.`);
      }
    }

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
  dataCheckEl.textContent = "Loading opportunity and startup data from the local backend…";
}

function renderDataCheckError(message) {
  dataCheckEl.className = "data-check data-check-error";
  dataCheckEl.innerHTML =
    "<strong>Data check not run.</strong> " +
    `${escapeHtml(message)} Records are not shown until the backend is reachable.`;
}

function renderDataCheck() {
  const opportunities = validateOpportunities(DATA.opportunities);
  const startups = validateStartups(DATA.startups);
  const issues = [...opportunities.issues, ...startups.issues];

  if (issues.length === 0) {
    dataCheckEl.className = "data-check";
    dataCheckEl.innerHTML =
      "<strong>Data check passed.</strong> " +
      `${opportunities.recordCount} opportunity records and ${startups.recordCount} startup profiles checked: ` +
      "required fields, dates, funding pairs, and verification rules are valid.";
  } else {
    dataCheckEl.className = "data-check data-check-error";
    dataCheckEl.innerHTML =
      `<strong>Data check found ${issues.length} issue(s).</strong>` +
      `<ul>${issues.map((issue) => `<li>${escapeHtml(issue)}</li>`).join("")}</ul>` +
      "<p>Fix the JSON in <code>backend/app/data/</code>, then reload this page.</p>";
    console.warn("Data check issues:", issues);
  }
}

// ---------- 6. Shared card pieces ----------

function statusBadge(record, kind) {
  if (record.dataStatus === "verified") {
    return '<span class="badge badge-verified">Verified</span>';
  }
  return `<span class="badge badge-demo">${kind === "startup" ? "Demo startup" : "Demo data"}</span>`;
}

function deadlineHtml(record) {
  const note = record.deadlineNote ? ` ${escapeHtml(record.deadlineNote)}` : "";

  if (record.applicationDeadline !== null) {
    return `
      <p class="deadline">
        <strong>Application deadline:</strong>
        <time datetime="${escapeHtml(record.applicationDeadline)}">${formatIsoDate(
      record.applicationDeadline
    )}</time>
        <span class="muted">as recorded — check the official source for changes.</span>${note}
      </p>`;
  }

  const demoNote =
    record.dataStatus === "demo" ? " This demo record has no real deadline." : "";
  return `
    <p class="deadline">
      <strong>Application deadline:</strong> Unknown — not recorded.${note}${demoNote}
    </p>`;
}

function eligibilityHtml(record) {
  if (record.eligibility === null) {
    return `
      <div class="info-block">
        <h4>Eligibility</h4>
        <p>Unknown — not recorded. Check the programme's own rules before applying.</p>
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

function sourceHtml(record, label) {
  if (record.sourceUrl !== null) {
    return `
      <p class="source">
        <a href="${escapeHtml(record.sourceUrl)}" target="_blank" rel="noopener noreferrer">
          ${escapeHtml(label || "Official source")}
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

function checklistItems(record) {
  const items = [];

  if (record.dataStatus === "demo") {
    items.push("This record is fictional — there is nothing to apply to.");
  }
  if (record.sourceUrl === null) {
    items.push("No official source is recorded, so the details cannot be confirmed.");
  }
  if (record.eligibility === null) {
    items.push("Eligibility is not recorded — check the programme's own eligibility rules.");
  }
  if (record.applicationDeadline === null) {
    items.push("The application deadline is not recorded — check the official page.");
  }

  items.push("Confirm the programme exists and is currently accepting applications.");
  items.push("Check fees, data handling, and any legal or regulatory requirements.");
  return items;
}

function matchBlockHtml(match, which) {
  if (!match) {
    return `
      <div class="match">
        <p class="preview-note">${escapeHtml(ROLE_CONFIG[which].previewNote)}</p>
      </div>`;
  }

  const percent = Math.max(0, Math.min(100, Number(match.percent) || 0));
  const reasons = Array.isArray(match.reasons) ? match.reasons : [];
  const missing = Array.isArray(match.missing) ? match.missing : [];
  const assessed = Array.isArray(match.assessed) ? match.assessed : [];

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
      ${
        which === "investor" && missing.length
          ? `<div class="missing">
              <h4>Information not available</h4>
              <ul>${missing.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
            </div>`
          : ""
      }
      ${
        which === "investor"
          ? `<p class="assessed-note">
              Criteria assessed: ${escapeHtml(assessed.length ? assessed.join(", ") : "none")}.
              Missing data is not treated as a negative signal.
            </p>`
          : ""
      }
      <p class="match-source">
        Rule-based score from the local backend — not ${
          which === "investor" ? "an investment recommendation or offer" : "an eligibility decision"
        }.
      </p>
    </div>`;
}

function opportunityCardHtml(record, match) {
  const fineprint =
    record.dataStatus === "demo"
      ? "Fictional demo record. Not a real programme and not evidence that funding or support is available."
      : `Verified record: details checked on ${formatIsoDate(
          record.lastVerifiedDate
        )}. Availability may change; always confirm on the official source.`;

  return `
    <article class="card">
      <div class="card-top">
        <span class="badge badge-category">${escapeHtml(record.category)}</span>
        ${statusBadge(record, "opportunity")}
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

      ${matchBlockHtml(match, "startup")}

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

function startupCardHtml(startup, match) {
  const dataNote =
    startup.dataStatus === "demo"
      ? "Demo startup — this profile is fictional. It is not a real investable business, and its metrics are illustrative."
      : `Verified profile: recorded details were checked against the source on ${formatIsoDate(
          startup.lastVerifiedDate
        )}. This does not guarantee the information is current.`;

  return `
    <article class="card">
      <div class="card-top">
        ${statusBadge(startup, "startup")}
        <span class="badge badge-category">${escapeHtml(startup.industry)}</span>
      </div>

      <h3>${escapeHtml(startup.name)}</h3>
      <p class="summary">${escapeHtml(startup.description)}</p>

      <p class="card-meta">
        <span><strong>Country:</strong> ${escapeHtml(startup.country)}</span>
        <span><strong>Industry:</strong> ${escapeHtml(startup.industry)}</span>
        <span><strong>Stage:</strong> ${escapeHtml(startup.stage)}</span>
        <span><strong>Business model:</strong> ${valueOrUnknown(startup.businessModel)}</span>
        <span><strong>Revenue status:</strong> ${valueOrUnknown(startup.revenueStatus)}</span>
        <span><strong>Funding sought:</strong> ${fundingText(startup)}</span>
      </p>

      ${matchBlockHtml(match, "investor")}

      <details class="verify">
        <summary>View details</summary>
        <p><strong>Data status:</strong> ${escapeHtml(dataNote)}</p>
        ${startup.notes ? `<p><strong>Record notes:</strong> ${escapeHtml(startup.notes)}</p>` : ""}
        ${verificationHtml(startup)}
        ${sourceHtml(startup, "Startup source")}
        <p class="no-contact">
          There is no contact, messaging, or introduction feature in this prototype.
          Nothing has been sent to a founder, and no investment process has started.
        </p>
      </details>

      <p class="fineprint">${escapeHtml(
        startup.dataStatus === "demo"
          ? "Fictional demo startup. Not available for investment, and no introduction is implied."
          : "Verified recorded details only. Not an offer or investment recommendation."
      )}</p>
    </article>
  `;
}

// ---------- 7. States ----------

function loadingHtml(which, scoring) {
  const config = ROLE_CONFIG[which];
  return `
    <div class="loading" role="status">
      <span class="spinner" aria-hidden="true"></span>
      <p><strong>${scoring ? escapeHtml(config.loadingText) : "Loading records…"}</strong></p>
      <p class="muted">
        ${scoring
          ? `Sending your profile to <code>${escapeHtml(API_BASE)}${escapeHtml(config.endpoint)}</code>`
          : `Reading records from <code>${escapeHtml(API_BASE)}${escapeHtml(config.listEndpoint)}</code>`}
      </p>
    </div>
  `;
}

function apiErrorHtml(message) {
  return `
    <div class="api-error" role="alert">
      <h3>Could not load data from the backend</h3>
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
        Expected API: <code>${escapeHtml(API_BASE)}</code> ·
        <a href="${escapeHtml(API_BASE)}/docs" target="_blank" rel="noopener noreferrer">API docs</a>
      </p>
      <button type="button" class="btn btn-primary" data-action="retry-load">Retry connection</button>
    </div>
  `;
}

function matchErrorHtml(which, message) {
  return `
    <div class="api-error" role="alert">
      <h3>Matching could not be completed</h3>
      <p><strong>What happened:</strong> ${escapeHtml(message)}</p>
      <p>
        No fallback results are shown, because stale or frontend-calculated scores would be
        misleading. Check that the backend is still running, then try again.
      </p>
      <p class="api-error-cmd">
        From the repository root:<br />
        <code>cd backend</code><br />
        <code>python -m uvicorn app.main:app --reload</code>
      </p>
      ${
        LAST_PAYLOAD[which]
          ? '<button type="button" class="btn btn-primary" data-action="retry-match">Try again</button>'
          : ""
      }
    </div>
  `;
}

function emptyHtml(which) {
  const config = ROLE_CONFIG[which];
  const records = DATA[config.dataKey];

  if (verifiedOnlyEl.checked) {
    return `
      <p class="empty">
        <strong>No verified ${escapeHtml(config.noun)} are available.</strong>
        All ${records.length} current records are clearly labelled demo data. A record appears
        here only after an official source URL and a verification date are added. Uncheck
        &ldquo;Verified records only&rdquo; to explore the demo set.
      </p>
    `;
  }

  if (records.length === 0) {
    return `
      <p class="empty">
        <strong>The backend returned no ${escapeHtml(config.noun)}.</strong>
        Add records to <code>${escapeHtml(config.dataFile)}</code> and reload this page.
      </p>
    `;
  }

  return `
    <p class="empty">
      No records to show with these options. Try another sort order, or uncheck
      &ldquo;Verified records only&rdquo;.
    </p>
  `;
}

// ---------- 8. Render results ----------

function currentConfig() {
  return role ? ROLE_CONFIG[role] : null;
}

function sortedItems(items) {
  const useMatch = sortEl.value === "match" && PROFILES[role];
  if (useMatch) {
    return items.sort(
      (a, b) =>
        (b.match ? b.match.percent : 0) - (a.match ? a.match.percent : 0) ||
        a.record.name.localeCompare(b.record.name)
    );
  }
  return items.sort((a, b) => a.record.name.localeCompare(b.record.name));
}

function renderResults() {
  if (!role) return;
  const config = ROLE_CONFIG[role];
  const records = DATA[config.dataKey];

  if (loadState === "loading") {
    summaryEl.textContent = "Loading records from the local backend…";
    countsEl.textContent = "";
    setNotice("");
    resultsEl.innerHTML = loadingHtml(role, false);
    return;
  }

  if (loadState === "error") {
    summaryEl.textContent = "Records could not be loaded. See the error below.";
    countsEl.textContent = "";
    setNotice("");
    resultsEl.innerHTML = apiErrorHtml(loadError);
    return;
  }

  const matchMap = MATCHES[role];
  const profile = PROFILES[role];

  let items = records.map((record) => ({
    record,
    match: profile ? matchMap.get(record.id) || null : null,
  }));

  if (verifiedOnlyEl.checked) {
    items = items.filter((item) => item.record.dataStatus === "verified");
  }

  sortedItems(items);

  const demoCount = items.filter((item) => item.record.dataStatus === "demo").length;
  const verifiedCount = items.length - demoCount;
  countsEl.textContent = `${items.length} shown of ${records.length} · ${demoCount} demo · ${verifiedCount} verified`;

  if (profile) {
    summaryEl.textContent =
      `Showing ${items.length} of ${records.length} ${config.noun}, ranked with the backend's ` +
      `rule-based score. Scores describe fit only, not ${role === "investor" ? "investment readiness" : "eligibility"}.`;
  } else {
    summaryEl.textContent =
      `Preview: showing ${items.length} of ${records.length} ${config.noun}. Not scored yet — ` +
      `complete the form and press “${config.action}”.`;
  }

  const info = RESPONSE_INFO[role];
  const allDemo = items.length > 0 && demoCount === items.length;
  if (info && info.warning) {
    setNotice(`<p>${escapeHtml(info.warning)}</p>`);
  } else if (allDemo) {
    setNotice(`
      <p>
        <strong>Demo-only results.</strong> Every record shown is fictional demo data from the
        hackathon. Nothing here is verified, available, or an offer.
      </p>
    `);
  } else {
    setNotice("");
  }

  if (items.length === 0) {
    resultsEl.innerHTML = emptyHtml(role);
    return;
  }

  resultsEl.innerHTML = items
    .map((item) =>
      role === "investor"
        ? startupCardHtml(item.record, item.match)
        : opportunityCardHtml(item.record, item.match)
    )
    .join("");
}

// ---------- 9. Load records ----------

async function loadData() {
  loadState = "loading";
  loadError = "";
  DATA.opportunities = [];
  DATA.startups = [];

  renderDataCheckPending();
  setSourceStatus(`Connecting to ${API_BASE}…`, "loading");
  if (role) renderResults();

  const results = await Promise.allSettled([
    fetchJson("/api/opportunities"),
    fetchJson("/api/startups"),
  ]);

  const failures = [];

  const opportunityResult = results[0];
  if (opportunityResult.status === "fulfilled" && Array.isArray(opportunityResult.value)) {
    DATA.opportunities = opportunityResult.value;
  } else {
    failures.push(
      opportunityResult.status === "fulfilled"
        ? "the opportunity response was not a list"
        : `opportunities: ${opportunityResult.reason.message}`
    );
  }

  const startupResult = results[1];
  if (startupResult.status === "fulfilled" && Array.isArray(startupResult.value)) {
    DATA.startups = startupResult.value;
  } else {
    failures.push(
      startupResult.status === "fulfilled"
        ? "the startup response was not a list"
        : `startups: ${startupResult.reason.message}`
    );
  }

  if (failures.length > 0) {
    loadState = "error";
    loadError = failures.join("; ");
    setSourceStatus(`Backend unavailable · ${API_BASE}`, "error");
    renderDataCheckError(`Could not read ${API_BASE} (${loadError}).`);
    if (role) renderResults();
    console.error("Data load failed:", loadError);
    return;
  }

  loadState = "ready";
  setSourceStatus(
    `Connected · ${DATA.opportunities.length} opportunities · ${DATA.startups.length} startup profiles`,
    "ready"
  );
  renderDataCheck();
  if (role) renderResults();
}

// ---------- 10. Role selection ----------

function syncRoleCards() {
  roleInputs.forEach((input) => {
    const card = input.closest(".role-card");
    if (card) card.classList.toggle("is-selected", input.checked);
  });
}

function selectRole(next) {
  const previous = role;
  role = next;
  const config = ROLE_CONFIG[next];

  workspaceEl.hidden = false;
  startupPanel.hidden = next !== "startup";
  investorPanel.hidden = next !== "investor";

  resultsHeadingEl.textContent = config.resultsTitle;
  explainerEl.innerHTML = config.explainer;
  sortEl.value = "match";

  const recovery =
    previous && previous !== next
      ? ` Your ${ROLE_CONFIG[previous].label} form entries were kept, so switching back will restore them.`
      : "";
  roleStatusEl.textContent = `${config.label} selected. The ${config.label.toLowerCase()} form is now active.${recovery}`;

  syncRoleCards();
  renderResults();

  if (loadState === "error") {
    // Keep the error visible but do not move focus unexpectedly.
    console.warn("Role selected while the backend was unavailable.");
  }
}

roleInputs.forEach((input) => {
  input.addEventListener("change", () => {
    if (input.checked) selectRole(input.value);
  });
});

// ---------- 11. Read profiles and validate ----------

function readOptionalAmount(input, label) {
  const raw = input.value.trim();
  if (raw === "") return { value: null };
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0) {
    return { error: `${label} must be 0 or more, or left blank.` };
  }
  return { value };
}

function readStartupProfile() {
  const country = $("startup-country").value;
  const industry = $("startup-industry").value;
  const stage = $("startup-stage").value;
  const goals = readChecked("startup-goals");
  const description = startupDescriptionEl.value.trim();
  const currency = $("startup-currency").value;

  const amount = readOptionalAmount($("startup-funding"), "The funding amount");
  if (amount.error) return { error: amount.error };

  if (amount.value !== null && !currency) {
    return { error: "Choose a currency for the funding amount, or clear the amount." };
  }
  if (amount.value === null && currency) {
    return { error: "Enter a funding amount as well, or set the currency back to “Select…”." };
  }

  const profile = {
    country,
    industry,
    stage,
    goals,
    fundingAmount: amount.value,
    fundingCurrency: amount.value === null ? null : currency,
    description,
    top_k: 50,
  };

  const hasDetail = Boolean(
    country || industry || stage || goals.length || amount.value !== null || description
  );

  return { profile, hasDetail };
}

function readInvestorProfile() {
  const investorType = $("investor-type").value;
  const countries = readChecked("investor-countries");
  const industries = readChecked("investor-industries");
  const stages = readChecked("investor-stages");
  const strategies = readChecked("investor-strategies");
  const goals = readChecked("investor-goals");
  const description = investorDescriptionEl.value.trim();
  const currency = $("investor-currency").value || "USD";

  const min = readOptionalAmount($("investor-ticket-min"), "The minimum ticket");
  if (min.error) return { error: min.error };
  const max = readOptionalAmount($("investor-ticket-max"), "The maximum ticket");
  if (max.error) return { error: max.error };

  if (min.value !== null && max.value !== null && min.value > max.value) {
    return { error: "The minimum ticket must be less than or equal to the maximum ticket." };
  }

  const profile = {
    investorType,
    countries,
    industries,
    stages,
    ticketMin: min.value,
    ticketMax: max.value,
    currency,
    strategies,
    goals,
    description,
    top_k: 50,
  };

  const hasDetail = Boolean(
    investorType ||
      countries.length ||
      industries.length ||
      stages.length ||
      strategies.length ||
      goals.length ||
      min.value !== null ||
      max.value !== null ||
      description
  );

  return { profile, hasDetail };
}

// ---------- 12. Matching requests ----------

async function runMatch(which, profile) {
  const config = ROLE_CONFIG[which];
  isBusy = true;
  setFormMessage(which, "");
  setBusy(which, true);
  LAST_PAYLOAD[which] = profile;

  summaryEl.textContent = config.loadingText;
  countsEl.textContent = "";
  setNotice("");
  resultsEl.innerHTML = loadingHtml(which, true);

  try {
    const data = await fetchJson(config.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    });

    if (!data || !Array.isArray(data.matches)) {
      throw new Error("the backend response did not include a matches list");
    }

    const map = new Map();
    data.matches.forEach((match) => {
      const record = which === "investor" ? match.startup : match.opportunity;
      if (record && record.id) map.set(record.id, match);
    });

    MATCHES[which] = map;
    PROFILES[which] = profile;
    RESPONSE_INFO[which] = data;

    if (role === which) {
      renderResults();
      if (window.innerWidth < 900) {
        resultsHeadingEl.scrollIntoView({ behavior: "smooth" });
      }
    }
  } catch (error) {
    console.error("Matching request failed:", error);
    MATCHES[which].clear();
    PROFILES[which] = null;
    RESPONSE_INFO[which] = null;

    if (role === which) {
      summaryEl.textContent =
        "Matching failed. No results are shown because the backend did not respond successfully.";
      countsEl.textContent = "";
      setNotice("");
      resultsEl.innerHTML = matchErrorHtml(which, error.message || String(error));
    }
    setFormMessage(
      which,
      `Could not get matches from the backend (${error.message || error}). ` +
        "Check that the backend is still running, then try again."
    );
  } finally {
    isBusy = false;
    setBusy(which, false);
  }
}

async function handleSubmit(which, reader) {
  if (isBusy) return;

  const result = reader();
  if (result.error) {
    setFormMessage(which, result.error);
    return;
  }
  if (!result.hasDetail) {
    setFormMessage(
      which,
      "Add at least one detail — such as a country, industry, stage, goal, ticket range, or description — so the rules have something to explain."
    );
    return;
  }
  if (loadState !== "ready") {
    setFormMessage(
      which,
      "Records are not loaded yet. Start the backend, press Retry connection, then try matching again."
    );
    return;
  }

  await runMatch(which, result.profile);
}

startupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleSubmit("startup", readStartupProfile);
});

investorForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleSubmit("investor", readInvestorProfile);
});

// ---------- 13. Sorting, filtering, reset, retry ----------

sortEl.addEventListener("change", renderResults);
verifiedOnlyEl.addEventListener("change", renderResults);

function bindCounter(input, output) {
  const update = () => {
    output.textContent = String(input.value.length);
  };
  input.addEventListener("input", update);
  update();
}

bindCounter(startupDescriptionEl, startupDescriptionCountEl);
bindCounter(investorDescriptionEl, investorDescriptionCountEl);

// "reset" fires before the fields clear, so wait one tick.
startupForm.addEventListener("reset", () => {
  window.setTimeout(() => {
    MATCHES.startup.clear();
    PROFILES.startup = null;
    RESPONSE_INFO.startup = null;
    LAST_PAYLOAD.startup = null;
    setFormMessage("startup", "");
    if (role === "startup") {
      sortEl.value = "match";
      renderResults();
    }
  }, 0);
});

investorForm.addEventListener("reset", () => {
  window.setTimeout(() => {
    MATCHES.investor.clear();
    PROFILES.investor = null;
    RESPONSE_INFO.investor = null;
    LAST_PAYLOAD.investor = null;
    setFormMessage("investor", "");
    if (role === "investor") {
      sortEl.value = "match";
      renderResults();
    }
  }, 0);
});

resultsEl.addEventListener("click", (event) => {
  const retryLoad = event.target.closest('[data-action="retry-load"]');
  if (retryLoad) {
    loadData();
    return;
  }

  const retryMatch = event.target.closest('[data-action="retry-match"]');
  if (retryMatch && role && LAST_PAYLOAD[role] && !isBusy) {
    runMatch(role, LAST_PAYLOAD[role]);
  }
});

// ---------- 14. First render ----------

function resetToNoRole() {
  role = null;
  roleInputs.forEach((input) => {
    input.checked = false;
  });
  syncRoleCards();
  workspaceEl.hidden = true;
  startupPanel.hidden = true;
  investorPanel.hidden = true;
  roleStatusEl.textContent =
    "No role selected yet. The matching forms and results stay hidden until you choose Startup Owner or Investor.";
  Object.keys(MATCHES).forEach((key) => MATCHES[key].clear());
  Object.keys(PROFILES).forEach((key) => {
    PROFILES[key] = null;
  });
  Object.keys(RESPONSE_INFO).forEach((key) => {
    RESPONSE_INFO[key] = null;
  });
  setFormMessage("startup", "");
  setFormMessage("investor", "");
}

/**
 * Browsers can restore form values and the checked role on back/forward. Start
 * from a neutral state so a live demo is always predictable.
 */
window.addEventListener("pageshow", (event) => {
  if (!event.persisted) return;
  resetToNoRole();
  loadData();
});

syncRoleCards();
loadData();

// Helpers available for debugging from the browser console.
window.ASEAN_GATEWAY = {
  API_BASE,
  validateOpportunities,
  validateStartups,
  loadData,
  get state() {
    return { role, loadState, loadError };
  },
};
