/*
 * data.js
 * ==================================================================
 * WHERE OPPORTUNITIES LIVE
 *
 * Everything in this file is plain JavaScript data, edited by hand.
 * There is no database and no build step: save the file, refresh the
 * browser, and the page updates.
 *
 * ------------------------------------------------------------------
 * THE THREE RULES
 * ------------------------------------------------------------------
 * 1. null means "we do not know".
 *    Never guess a deadline, eligibility rule, or target group.
 *    null  = unknown
 *    []    = we checked and there is nothing to list
 *    value = we checked and this is what we found
 *
 * 2. "Any" is not the same as null.
 *    targetStages: ["Any"]  -> openly available to every stage
 *    targetStages: null     -> we do not know who it targets
 *
 * 3. A record can only be dataStatus: "verified" when BOTH
 *    sourceUrl and lastVerifiedDate are filled in with real evidence.
 *    "verified" refers to the RECORDED INFORMATION on the stated date,
 *    not to whether applications are open today.
 *
 * ------------------------------------------------------------------
 * TEMPLATE - copy this to add a record
 * ------------------------------------------------------------------
 *
 *  {
 *    id: "unique-lowercase-id",
 *    name: "Name of the opportunity",
 *    provider: "Organisation that runs it",
 *    category: "Funding",              // "Funding" | "Support" | "Partnership"
 *    description: "One or two plain sentences.",
 *    countries: ["Malaysia"],          // or ["ASEAN-wide"]
 *    targetStages: null,               // e.g. ["Seed"] or ["Any"] or null
 *    targetIndustries: null,           // e.g. ["Fintech"] or ["Any"] or null
 *    goals: ["Funding"],               // which user goals it may serve
 *    eligibility: null,                // null = unknown, [] = none stated
 *    applicationDeadline: null,        // "YYYY-MM-DD" or null
 *    deadlineNote: null,               // optional short note
 *    dataStatus: "demo",               // "demo" | "verified"
 *    sourceUrl: null,                  // official URL, required if verified
 *    lastVerifiedDate: null,           // "YYYY-MM-DD", required if verified
 *    notes: "Why this record exists."
 *  }
 *
 * ------------------------------------------------------------------
 * CURRENT FILE: 12 DEMO RECORDS, 0 VERIFIED RECORDS
 * All records below are fictional examples written for the hackathon.
 * They are NOT real programmes and do not prove that anything exists,
 * is open, or is accepting applications.
 * ==================================================================
 */

const SCHEMA_VERSION = 2;

const DEMO_NOTE =
  "Fictional example written for the hackathon. Not a real programme, " +
  "provider, deadline, or eligibility rule.";

const OPPORTUNITIES = [
  {
    id: "demo-fund-01",
    name: "ASEAN-Wide Demo Seed Grant (Illustrative)",
    provider: "Illustrative Example Provider A",
    category: "Funding",
    description:
      "Fictional small grant example for early-stage teams that also want a mentor for six months.",
    countries: ["ASEAN-wide"],
    targetStages: ["Pre-seed", "Seed"],
    targetIndustries: ["Any"],
    goals: ["Funding", "Mentorship"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-fund-02",
    name: "AgriFood Innovation Fund - Demo Record",
    provider: "Illustrative Example Provider B",
    category: "Funding",
    description:
      "Made-up fund example for food and agriculture startups expanding into neighbouring markets.",
    countries: ["Malaysia", "Thailand", "Vietnam"],
    targetStages: ["Seed", "Growth"],
    targetIndustries: ["AgriFood"],
    goals: ["Funding", "Market access"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-support-01",
    name: "Fintech Sandbox Support Track (Demo)",
    provider: "Illustrative Example Provider C",
    category: "Support",
    description:
      "Example support track for fintech teams that need regulatory guidance while testing a product.",
    countries: ["Singapore", "Indonesia", "Philippines"],
    targetStages: ["Seed", "Growth"],
    targetIndustries: ["Fintech"],
    goals: ["Regulatory guidance", "Mentorship"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-partner-01",
    name: "Green Logistics Partnership Network - Demo",
    provider: "Illustrative Example Provider D",
    category: "Partnership",
    description:
      "Fictional network of logistics and sustainability partners for growth-stage pilot projects.",
    countries: ["ASEAN-wide"],
    targetStages: ["Growth"],
    targetIndustries: ["Logistics", "Climate / GreenTech"],
    goals: ["Partnership", "Market access"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-partner-02",
    name: "HealthTech Pilot Matching (Demo)",
    provider: "Illustrative Example Provider E",
    category: "Partnership",
    description:
      "Made-up matchmaking example between health startups and clinics for small pilot studies.",
    countries: ["Malaysia", "Singapore", "Thailand"],
    targetStages: ["Pre-seed", "Seed"],
    targetIndustries: ["HealthTech"],
    goals: ["Partnership", "Funding"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-support-02",
    name: "EdTech Incubator Residency (Demo)",
    provider: "Illustrative Example Provider F",
    category: "Support",
    description:
      "Example residency with workspace and weekly mentoring for very early education startups.",
    countries: ["Indonesia", "Vietnam", "Philippines"],
    targetStages: ["Idea", "Pre-seed"],
    targetIndustries: ["EdTech"],
    goals: ["Incubation & workspace", "Mentorship"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-fund-03",
    name: "Tourism Digital Boost Grant - Demo",
    provider: "Illustrative Example Provider G",
    category: "Funding",
    description:
      "Fictional grant example for tourism SMEs building digital booking or guest-experience tools.",
    countries: ["Thailand", "Malaysia", "Indonesia"],
    targetStages: ["Idea", "Pre-seed", "Seed"],
    targetIndustries: ["Tourism"],
    goals: ["Funding", "Market access"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-support-03",
    name: "SaaS Talent Bridge Programme (Demo)",
    provider: "Illustrative Example Provider H",
    category: "Support",
    description:
      "Made-up programme example that helps software teams meet engineers and mentors across ASEAN.",
    countries: ["ASEAN-wide"],
    targetStages: ["Seed", "Growth"],
    targetIndustries: ["SaaS / Digital"],
    goals: ["Talent & hiring", "Mentorship"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-partner-03",
    name: "Creative Industries Showcase Partnership (Demo)",
    provider: "Illustrative Example Provider I",
    category: "Partnership",
    description:
      "Example partnership for creative teams to co-host showcases with regional partners.",
    countries: ["ASEAN-wide"],
    targetStages: ["Any"],
    targetIndustries: ["Creative industries"],
    goals: ["Partnership", "Market access"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-fund-04",
    name: "Manufacturing Automation Demo Fund",
    provider: "Illustrative Example Provider J",
    category: "Funding",
    description:
      "Fictional funding example for factories and industrial software teams adopting automation.",
    countries: ["Vietnam", "Thailand", "Indonesia"],
    targetStages: ["Growth"],
    targetIndustries: ["Manufacturing"],
    goals: ["Funding", "Partnership"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-support-04",
    name: "Women-Led Startup Demo Fellowship",
    provider: "Illustrative Example Provider K",
    category: "Support",
    description:
      "Example fellowship with mentoring and a small stipend for women-led early-stage teams.",
    countries: ["ASEAN-wide"],
    targetStages: ["Idea", "Pre-seed"],
    targetIndustries: ["Any"],
    goals: ["Mentorship", "Funding"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
  {
    id: "demo-partner-04",
    name: "Climate Resilience Joint Venture Match (Demo)",
    provider: "Illustrative Example Provider L",
    category: "Partnership",
    description:
      "Made-up matchmaking example for climate startups seeking corporate pilot partners.",
    countries: ["ASEAN-wide"],
    targetStages: ["Seed", "Growth"],
    targetIndustries: ["Climate / GreenTech"],
    goals: ["Partnership", "Funding"],
    eligibility: null,
    applicationDeadline: null,
    deadlineNote: null,
    dataStatus: "demo",
    sourceUrl: null,
    lastVerifiedDate: null,
    notes: DEMO_NOTE,
  },
];
