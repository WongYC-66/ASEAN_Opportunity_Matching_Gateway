/*
 * app.js
 * ==================================================================
 * The whole "brain" of the prototype, in plain JavaScript.
 *
 * It does four things:
 *   1. Checks the data in data.js for mistakes (validateOpportunities).
 *   2. Scores each record against the startup form.
 *   3. Filters/searches the records.
 *   4. Draws the cards, including why a record may fit, its deadline,
 *      eligibility, source, and verification status.
 *
 * There is no server, no framework, and no API call.
 * ==================================================================
 */

// ---------- 1. Page elements ----------
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

const CATEGORIES = ["Funding", "Support", "Partnership"];
const ALLOWED_STATUSES = ["demo", "verified"];

// Highest possible score in scoreOpportunity() below.
const MAX_SCORE = 3 + 2 + 2 + 2; // = 9

// null = preview mode (the form has not been submitted yet).
let profile = null;

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

// ---------- 3. Data validation ----------

/**
 * Check every record for obvious mistakes.
 *
 * Returns { recordCount, issues: [ "message", ... ] }.
 * The page shows the result in the "Data check" box, and the browser
 * console shows details too, so a beginner can fix data.js directly.
 */
function validateOpportunities(records) {
  const issues = [];
  const seenIds = new Set();
  const today = todayIso();

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
      "<p>Fix these in <code>data.js</code>, then refresh the page.</p>";
  }

  // Also log details for anyone with developer tools open.
  if (result.issues.length > 0) {
    console.warn("Data check issues:", result.issues);
  }
}

// ---------- 4. Matching logic ----------

/**
 * Compare one record with the user's profile.
 *
 * Points (simple and explainable):
 *   country  exact match = 3, "ASEAN-wide" = 2
 *   industry exact match = 2, "Any" = 1, unknown (null) = 0
 *   stage    exact match = 2, "Any" = 1, unknown (null) = 0
 *   goals    1 point per shared goal, capped at 2
 *
 * dataStatus is deliberately NOT scored.
 */
function scoreOpportunity(record, userProfile) {
  let score = 0;
  const reasons = [];

  if (userProfile.country) {
    if (record.countries.includes(userProfile.country)) {
      score += 3;
      reasons.push(`Covers your country (${userProfile.country}).`);
    } else if (record.countries.includes("ASEAN-wide")) {
      score += 2;
      reasons.push("Listed as ASEAN-wide, so your country is in scope.");
    }
  }

  if (userProfile.industry && record.targetIndustries !== null) {
    if (record.targetIndustries.includes(userProfile.industry)) {
      score += 2;
      reasons.push(`Focused on your industry (${userProfile.industry}).`);
    } else if (record.targetIndustries.includes("Any")) {
      score += 1;
      reasons.push("Open to any industry.");
    }
  }

  if (userProfile.stage && record.targetStages !== null) {
    if (record.targetStages.includes(userProfile.stage)) {
      score += 2;
      reasons.push(`Intended for ${userProfile.stage} companies.`);
    } else if (record.targetStages.includes("Any")) {
      score += 1;
      reasons.push("Open to any company stage.");
    }
  }

  const sharedGoals = record.goals.filter((goal) => userProfile.goals.includes(goal));
  if (sharedGoals.length > 0) {
    score += Math.min(sharedGoals.length, 2);
    reasons.push(`Matches your goal: ${sharedGoals.join(", ")}.`);
  }

  if (reasons.length === 0) {
    reasons.push(
      "No direct match with the details you entered - shown only as a record in the list."
    );
  }

  const percent = Math.round((score / MAX_SCORE) * 100);
  return { score, percent, reasons };
}

function matchLabel(percent) {
  if (percent >= 70) return "Strong match";
  if (percent >= 40) return "Possible match";
  if (percent > 0) return "Weak match";
  return "No direct match";
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

function cardHtml(record, match) {
  const matchBlock = match
    ? `
      <div class="match">
        <div class="match-head">
          <span class="match-label">${escapeHtml(matchLabel(match.percent))}</span>
          <span class="match-percent">${match.percent}%</span>
        </div>
        <div class="meter" role="img" aria-label="Match strength: ${match.percent} percent">
          <span style="width: ${match.percent}%"></span>
        </div>
        <h4>Why this may be relevant</h4>
        <ul class="reasons">
          ${match.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
        </ul>
      </div>`
    : `
      <div class="match">
        <p class="preview-note">
          Preview only - fill in your startup details and press
          &ldquo;Find opportunities&rdquo; to see a match score and reasons.
        </p>
      </div>`;

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

      ${matchBlock}

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

  return `
    <p class="empty">
      No records match these filters. Try clearing the search box, choosing
      &ldquo;All types&rdquo;, or switching the record status back to &ldquo;All records&rdquo;.
    </p>
  `;
}

// ---------- 6. Filter, sort, render ----------

function updateCounts() {
  const demoCount = OPPORTUNITIES.filter((record) => record.dataStatus === "demo").length;
  const verifiedCount = OPPORTUNITIES.filter((record) => record.dataStatus === "verified").length;
  countsEl.textContent = `${OPPORTUNITIES.length} records: ${verifiedCount} verified, ${demoCount} demo.`;
}

function applyFilters() {
  const selectedType = typeFilterEl.value;
  const selectedStatus = statusFilterEl.value;
  const query = searchEl.value.trim().toLowerCase();
  const sortMode = sortEl.value;

  let items = OPPORTUNITIES.map((record) => ({
    record,
    match: profile ? scoreOpportunity(record, profile) : null,
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
      (a, b) => b.match.percent - a.match.percent || a.record.name.localeCompare(b.record.name)
    );
  } else {
    items.sort((a, b) => a.record.name.localeCompare(b.record.name));
  }

  const total = OPPORTUNITIES.length;
  summaryEl.textContent = profile
    ? `Showing ${items.length} of ${total} records, ranked for your profile.`
    : `Preview mode: showing ${items.length} of ${total} records. Fill in the form and press "Find opportunities" to see ranked matches.`;

  resultsEl.innerHTML =
    items.length === 0
      ? emptyHtml()
      : items.map((item) => cardHtml(item.record, item.match)).join("");
}

// ---------- 7. Events ----------

function readProfile() {
  const checkedGoals = formEl.querySelectorAll('input[name="goals"]:checked');
  return {
    country: countryEl.value,
    industry: industryEl.value,
    stage: stageEl.value,
    goals: Array.from(checkedGoals).map((checkbox) => checkbox.value),
  };
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();

  const candidate = readProfile();
  const hasAnyDetail =
    candidate.country ||
    candidate.industry ||
    candidate.stage ||
    candidate.goals.length > 0;

  if (!hasAnyDetail) {
    formMessageEl.textContent =
      "Please choose at least one detail - country, industry, stage, or a goal - so we can explain the matches.";
    formMessageEl.hidden = false;
    return;
  }

  formMessageEl.textContent = "";
  formMessageEl.hidden = true;
  profile = candidate;
  applyFilters();

  if (window.innerWidth < 900) {
    document.getElementById("results-heading").scrollIntoView({ behavior: "smooth" });
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
    formMessageEl.textContent = "";
    formMessageEl.hidden = true;
    applyFilters();
  }, 0);
});

// ---------- 8. First render ----------
renderDataCheck();
updateCounts();
applyFilters();

/**
 * Browsers can restore form values after a reload, which would leave the
 * fields filled in while the results show preview mode. Reset on pageshow
 * so the page always starts in one consistent state for a live demo.
 */
window.addEventListener("pageshow", () => {
  formEl.reset();
  profile = null;
  formMessageEl.textContent = "";
  formMessageEl.hidden = true;
  renderDataCheck();
  updateCounts();
  applyFilters();
});

// Make the validation helper available to a console or a future test page.
window.validateOpportunities = validateOpportunities;
window.scoreOpportunity = scoreOpportunity;
window.renderDataCheck = renderDataCheck;
