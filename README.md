# ASEAN Opportunity Gateway

**One Gateway. Two Sides. A More Connected ASEAN Ecosystem.**

## Problem Statement

### Challenge #2 — Ecosystem Gateway

ASEAN's startup ecosystem is fragmented across different countries, organisations, funding programmes, accelerators, investors and business networks.

Startup founders often struggle to identify relevant funding opportunities, support programmes and strategic partners. Meanwhile, investors face difficulties discovering startups that align with their preferred markets, industries, investment stages and strategies.

There is no simple, unified discovery experience that effectively serves both sides.

## Our Solution

ASEAN Opportunity Gateway is a two-sided discovery and matching platform designed to connect startup founders with relevant ecosystem opportunities and help investors discover startups aligned with their investment preferences.

The platform provides two dedicated experiences:

1. **Startup Owner**

   Founders can specify their operating country, industry, startup stage, goals and funding requirements. The platform ranks relevant opportunities such as funding programmes, incubation support, mentorship and strategic partnerships.

2. **Investor**

   Investors can define their preferred geographies, industries, startup stages, investment ticket sizes, strategies and investment goals. The platform matches these preferences against startup profiles.

## How It Works

Users first select whether they are a Startup Owner or an Investor.

They then complete a profile based on their respective needs and preferences.

The frontend sends the profile to a Python backend through API requests. The backend processes the information using a deterministic, rule-based matching engine and structured JSON datasets.

Results are ranked according to relevant matching criteria, with scores and plain-language explanations showing why each opportunity or startup is relevant.

The platform also highlights missing information and distinguishes demo records from verified information to improve transparency.

## Technologies and Tools

- **HTML, CSS and JavaScript:** Frontend interface and user interactions.
- **Python:** Backend API and matching engine.
- **JSON:** Lightweight structured data storage for opportunities and startup profiles.
- **REST APIs:** Communication between the frontend and backend.
- **Git and GitHub:** Version control and team collaboration.
- **OpenCode:** AI-assisted development workflow.

## Target Users

- Startup founders and early-stage entrepreneurs across ASEAN.
- Angel investors and venture capital funds.
- Corporate venture capital teams.
- Family offices and strategic investors.
- Other participants in the ASEAN startup ecosystem.

## What Makes Our Solution Unique

1. **Two-Sided Matching**

   Unlike a conventional opportunity directory, the platform supports both startup-to-opportunity discovery and investor-to-startup discovery.

2. **Explainable Matching**

   Recommendations are not simply displayed as a list. Each result includes a matching score and explanations of the criteria that contributed to its relevance.

3. **Profile-Driven Discovery**

   Different users receive different results based on their country, industry, startup stage, goals and investment preferences.

4. **Transparent Data Handling**

   The platform distinguishes demo data from verified information and identifies unknown information rather than presenting assumptions as facts.

5. **Lightweight and Extensible Architecture**

   A Python backend, API-based integration and JSON storage provide a lightweight foundation that can be extended with verified ecosystem data, additional ASEAN markets and future integrations.

## Vision

We envision ASEAN Opportunity Gateway as a unified entry point where startup founders can discover the resources they need and investors can discover businesses that align with their investment interests — helping create a more connected and accessible ASEAN startup ecosystem.

> **Note:** The current prototype uses synthetic demonstration records to demonstrate the matching mechanism. These records do not represent actual funding programmes, verified startups or live investment opportunities.
