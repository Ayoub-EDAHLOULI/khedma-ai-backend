# AI Job-Search Agent — Technical Documentation (v2)

## 1. What we're building

A personal AI agent, **built to be self-hosted rather than run as a live public service**, that:

1. Pulls job postings from multiple platforms — real LinkedIn/Indeed/Moroccan-site data via a personal scraper module, plus legitimate aggregator APIs for markets they cover
2. Lets you search/chat in **Darija, French, Arabic, or English** — it detects the language and replies in the same one
3. Lets you choose **Local** (jobs in your country only) or **International** (worldwide, but filtered to remote/visa-sponsored/relocation-friendly roles you can _actually_ apply to — not random on-site jobs in a country you have no ties to)
4. Scores/ranks postings against your profile
5. Generates a tailored CV + cover letter per posting

**v1 → v2 change:** originally scoped as a hosted product anyone could sign up to. After checking Adzuna's coverage (no Morocco) and the legal history around scraping-as-a-business (see section 2a), the project is now scoped as **a personal tool you run yourself, published as open-source code others self-host** — same pattern as the well-known `JobSpy` library (MIT-licensed, scrapes LinkedIn/Indeed/Glassdoor/etc., run individually by each user). This removes the main legal exposure entirely, because there's no central service scraping at scale on anyone's behalf.

---

## 2. Reality check on data sources (read this before building anything)

This is the part that makes or breaks the project, so it comes first.

| Source                | Official public API?                                 | Reality                                                                                                                                                                                                                                                                                                                             |
| --------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LinkedIn**          | No general-purpose public jobs API                   | Jobs search is not open. Personal scraping is the practical route for real coverage (see 2a)                                                                                                                                                                                                                                        |
| **Indeed**            | Publisher API discontinued for new signups years ago | Same story — scraping is the practical route                                                                                                                                                                                                                                                                                        |
| **Aggregator APIs**   | Yes                                                  | **Adzuna** (free tier, but no Morocco coverage — confirmed from the country list), **JSearch on RapidAPI** (aggregates Google for Jobs), **Jooble API**, **Arbeitnow** (EU/Germany-focused, fully open), **RemoteOK / Remotive** (remote-only), **USAJobs** (US government) — good for the countries they cover, none cover Morocco |
| **Moroccan-specific** | No public API for any of these                       | **Rekrute.com** (largest Moroccan board), **Emploi.ma**, **ANAPEC** (national employment agency, public listings), **Bayt.com** (pan-MENA, has real Morocco/Gulf coverage) — scraping is the only option here too                                                                                                                   |

### 2a. Why scraping is fine here, in this shape, but wasn't in the original plan

- **hiQ Labs v. LinkedIn** (the landmark U.S. case) established that scraping _publicly visible_ data isn't a crime under the CFAA — but hiQ still lost, on **breach-of-contract** grounds (violating LinkedIn's ToS), and paid $500k in damages. What killed hiQ was being **a company scraping at scale and reselling the data as a hosted service** — a single, identifiable, commercially-motivated target.
- Running a scraper **personally, on your own account/IP, for your own job search** carries realistic risk of "your account gets rate-limited or banned" — not a lawsuit. Nobody sues an individual for checking job listings.
- Publishing the **code** as open source (not a hosted service) means each person who runs it does so on their own account, at their own risk, same as the `JobSpy` project (LinkedIn/Indeed/Glassdoor/ZipRecruiter/Bayt scraper, MIT license, thousands of stars, actively maintained for years). There is no central operator to go after.
- **The one thing to avoid**: hosting this centrally and offering it as a live signup product that scrapes on everyone's behalf. That recreates hiQ's exact position — a single company scraping at scale and monetizing it.

**Practical scraping notes** (learned from JobSpy's public experience): Indeed is currently the most scrape-tolerant of the two; LinkedIn rate-limits aggressively (often within ~10 pages from one IP) and effectively requires proxies for any real volume. Build in backoff/retry and expect to maintain the scraper as both sites change their markup — this is ongoing maintenance, not a one-time script.

**Recommendation:** pluggable source architecture (section 3) where:

- **Scraper module** (personal-use, own account) → LinkedIn, Indeed, Rekrute, Emploi.ma, ANAPEC, Bayt — this is what gives you real Morocco/local coverage and the two big global platforms.
- **API module** → Adzuna, Arbeitnow, JSearch, Remotive — free, legal, zero-maintenance, but skip Morocco entirely; useful for the "international" side (EU/US remote roles).
  Both modules write into the same `jobs` table (section 4) — the rest of the pipeline doesn't care which module a posting came from.

---

## 3. Stack decision

Your existing skills: .NET 8/C#, React, Next.js, Express.js, PostgreSQL, Python (ML/LLMs).

| Layer               | Option A                      | Option B        | Recommendation                                                                                                                                                                                                                                                                                                                                                               |
| ------------------- | ----------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API / orchestration | Express.js                    | FastAPI         | **FastAPI** — the matching + LLM + multilingual layer all live in Python anyway (embeddings, prompt orchestration, CV generation). Keeping one backend language avoids a cross-service call for every request.                                                                                                                                                               |
| Frontend            | Next.js                       | React (Vite)    | **Next.js** — you already use it daily, server actions make calling your FastAPI backend clean, and you get routing/SSR for free if you ever want to share this.                                                                                                                                                                                                             |
| Database            | PostgreSQL                    | —               | **PostgreSQL** — store raw postings, normalized postings, user profile, match scores, generated documents. Use `pgvector` extension for embedding similarity search instead of a separate vector DB — one less moving part.                                                                                                                                                  |
| Job fetching        | Scheduled job in same backend | Separate worker | **Separate lightweight worker** (a Python script run via cron / APScheduler / a simple queue) — keeps slow, rate-limited fetch jobs from blocking your API. Scraper sub-module uses Playwright (handles JS-rendered pages, more resilient than requests+BeautifulSoup for LinkedIn/Indeed) with your own logged-in session for LinkedIn; API sub-module is plain HTTP calls. |
| LLM                 | —                             | —               | Any capable model via API (Claude, GPT, Gemini) — multilingual handling below doesn't depend on which one.                                                                                                                                                                                                                                                                   |

This gives you: **Next.js (frontend) → FastAPI (backend/API + matching + LLM orchestration) → PostgreSQL + pgvector (storage) ← scheduled Python fetch worker (ingestion)**.

You could swap FastAPI for Express + a Python microservice just for the LLM/matching parts if you'd rather write the API in TS — reasonable, just adds one more network hop per request.

---

## 4. Data model (PostgreSQL)

```sql
-- Raw + normalized job postings
create table jobs (
  id uuid primary key default gen_random_uuid(),
  source text not null,              -- 'jsearch', 'adzuna', 'arbeitnow', ...
  source_job_id text not null,       -- id from the source, for de-duplication
  title text not null,
  company text,
  country text,                      -- ISO country code, normalized
  city text,
  is_remote boolean default false,
  visa_sponsorship boolean,          -- nullable = unknown
  scope text check (scope in ('local','international')), -- derived, see section 6
  description text,
  raw_json jsonb,                    -- full original payload, for reprocessing later
  posted_at timestamptz,
  fetched_at timestamptz default now(),
  embedding vector(1536),            -- pgvector, from description embedding
  unique(source, source_job_id)
);

-- Your profile (one row per user if you ever go multi-user; one row is fine solo)
create table profiles (
  id uuid primary key default gen_random_uuid(),
  full_name text,
  base_country text,                 -- your home country, drives "local" filtering
  cv_text text,                      -- plain-text extracted CV
  skills text[],
  preferred_languages text[],        -- ['darija','fr','ar','en']
  embedding vector(1536),            -- embedding of cv_text + skills
  created_at timestamptz default now()
);

-- Computed matches
create table matches (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs(id),
  profile_id uuid references profiles(id),
  score numeric,                     -- 0-1 similarity/relevance score
  reasoning text,                    -- short LLM-generated "why this matches"
  created_at timestamptz default now(),
  unique(job_id, profile_id)
);

-- Generated application packages
create table applications (
  id uuid primary key default gen_random_uuid(),
  match_id uuid references matches(id),
  tailored_cv text,
  cover_letter text,
  status text default 'draft',       -- draft, applied, rejected, interview...
  created_at timestamptz default now()
);
```

---

## 5. Multilingual chat layer (Darija / French / Arabic / English)

This is simpler than it looks — you don't need separate NLP pipelines per language. One well-prompted LLM call handles all of it:

**System prompt pattern:**

```
You are a job-search assistant. The user may write in Darija (Moroccan Arabic,
often in Latin script), Modern Standard Arabic, French, or English — sometimes
mixed. Detect the language used and reply in that same language and script.

From the user's message, extract a structured search query:
{
  "role_keywords": [...],
  "skills": [...],
  "location_scope": "local" | "international" | null,
  "remote_only": boolean,
  "seniority": string | null
}

If the request is ambiguous, ask one short clarifying question in the same
language the user used.
```

Practical notes:

- Darija written in Latin letters (e.g. "3andi 5 sn9a f React") is the trickiest case — modern frontier LLMs (Claude, GPT-4o/5-class, Gemini) handle this reasonably well already; no fine-tuning needed for v1.
- Keep language detection and query extraction in **one LLM call** — don't build a separate classifier first, it adds latency for no real gain at this scale.
- Store the extracted structured query, not just the raw text — that's what actually drives the SQL/vector filtering.

---

## 6. Local vs. International logic

This was your key requirement, so it gets its own section. The goal: "International" should mean _jobs you can realistically apply to and get_, not every job on Earth.

**Classification rule applied when a job is ingested (or on the fly):**

```
scope = 'local'          if job.country == profile.base_country
scope = 'international'  if job.is_remote == true
                          OR job.visa_sponsorship == true
                          OR job.country in profile.target_countries (explicit opt-in list)
scope = discard/hide      otherwise (on-site job, no sponsorship, different country —
                                     not realistically applicable)
```

**In the UI/chat**, the user picks a mode:

- **Local mode** → query filters `country = base_country`, remote or on-site both fine.
- **International mode** → query filters `scope = 'international'` per the rule above, so it's remote-friendly or sponsorship-flagged roles only, across countries.

**Where does `visa_sponsorship` and `is_remote` come from?** Aggregator APIs vary in how well they tag this:

- JSearch/Google for Jobs: has a `job_is_remote` boolean field — reliable enough to use directly.
- Adzuna: no explicit remote flag in most regions — you'll need a lightweight heuristic (regex/LLM classification on the description for "remote", "work from home", "visa sponsorship available", etc.) run once at ingestion time and cached in the `is_remote`/`visa_sponsorship` columns, rather than re-checked on every query.
- Arbeitnow: has explicit remote tagging.

Build this classification as a small ingestion-time enrichment step (rule-based first, LLM fallback for ambiguous descriptions) rather than deciding it at query time — much cheaper.

---

## 7. Matching pipeline

1. **Embed** the profile once (CV text + skills) → store in `profiles.embedding`.
2. **Embed** each job description at ingestion time → store in `jobs.embedding`.
3. On search, run a **pgvector cosine similarity** query filtered by the local/international scope and the structured query from section 5, to get a shortlist (e.g. top 30).
4. Send that shortlist + profile to the LLM for a **second-pass re-rank**: ask it to score 0-100 and give a one-line reason per job. This catches nuance embeddings miss (e.g. seniority mismatch, a skill listed as required vs. nice-to-have).
5. Return the top 3-5 to the user, ranked, with the score and reason.

This two-stage approach (cheap vector search → precise LLM re-rank on a small shortlist) keeps LLM costs down — you're never sending hundreds of job descriptions through the model per search.

---

## 8. Application generation (tailored CV + cover letter)

Per selected match:

1. Pull `profile.cv_text` and `job.description`.
2. One LLM call, prompted to: rewrite/reorder CV bullet points to foreground the most relevant experience for _this_ job (never fabricate experience you don't have), and draft a cover letter referencing 2-3 concrete overlaps between the job and your background.
3. Store both in `applications`, render as downloadable PDF/DOCX (reuse your existing PDF/DOCX generation skills) and/or plain text.
4. Let the user edit before "applying" — this should assist, not auto-submit applications. Auto-submitting to real employers on your behalf is a bad idea (rate limits, ToS, and you want to review before your name goes out).

---

## 9. API endpoints (FastAPI)

```
POST /profile                 create/update your profile + CV
POST /search                  { message: str }  → detects language, extracts query,
                               returns ranked matches
GET  /jobs/{id}                job detail
POST /matches/{id}/prepare     generates tailored CV + cover letter for a match
GET  /applications             list your application packages + status
PATCH /applications/{id}       update status (applied/rejected/interview)
```

Fetch worker runs separately (cron/APScheduler), writing into `jobs` — it has no HTTP endpoints, it's a background process.

---

## 10. Build order / milestones

**Milestone 1 — Ingestion only**

- Start with the **API module** (Adzuna + Arbeitnow, zero setup, zero risk) to get the pipeline end-to-end working. In parallel, build the **scraper module** for Rekrute/Emploi.ma/ANAPEC first (static HTML, no anti-bot, easiest wins for real Morocco data) before tackling LinkedIn/Indeed (JS-heavy, rate-limited, need your own logged-in session + Playwright). Land everything in `jobs`, no AI yet.

**Milestone 2 — Matching**

- Add profile table, embeddings, pgvector search, and the local/international scope rule. Verify search returns sane results before adding chat.

**Milestone 3 — Multilingual chat**

- Add the `/search` endpoint with the language-detecting LLM prompt from section 5. Test with real Darija/French/Arabic input.

**Milestone 4 — Application generation**

- Add `/matches/{id}/prepare`, tailored CV + cover letter generation, PDF export.

**Milestone 5 — Frontend polish**

- Next.js UI: search bar, match cards with scores, application package view. Skip the 3D avatar — it's pure decoration; revisit only if you want the demo flash later.

---

## 11. Open decisions before you start coding

- Single-user (just you) or multi-user for people who self-host their own instance? Either way, no central hosted signup — see section 12.
- Where does `target_countries` (the explicit international opt-in list) get set — a fixed setting, or something the chat can update conversationally ("search me jobs in France too")?
- How much scraper maintenance are you willing to take on? LinkedIn/Indeed change their markup periodically; budget occasional fix-up time, same as any project depending on `JobSpy`-style scraping does.

---

## 12. Distribution model: personal tool, open-sourced

Since this isn't a hosted product, "shipping" it means publishing a repo people clone and run themselves — not deploying a server with public signup.

**What changes vs. a normal SaaS repo:**

- **Config, not a login system.** Each person's own profile/CV, target countries, and LinkedIn session cookie (for the scraper) live in a local `.env` / config file — never sent to you, never centralized.
- **README must include a clear disclaimer**, plainly stated near the top, not buried:
  - This tool scrapes public job listings for personal use; scraping may violate the target sites' Terms of Service.
  - You are responsible for how you use it; the maintainer isn't operating a service on your behalf and provides no guarantee the scrapers keep working as sites change.
  - Not affiliated with, endorsed by, or connected to LinkedIn, Indeed, or any job board referenced.
  - This is the same posture `JobSpy` and similar open-source scrapers take.
- **Rate-limit responsibly by default** — ship conservative delays/backoff out of the box rather than "as fast as possible" settings, so people who clone it don't immediately get their accounts flagged.
- **Mobile app** (your stretch goal): just another client hitting the same FastAPI backend — each person still runs their _own_ backend instance (self-hosted, e.g. on their own VPS or even a Raspberry Pi / home server), the mobile app just points at their own instance's URL. No shared backend across users.

This keeps the "for anyone" goal alive — anyone _can_ run it — without you becoming the single operator holding everyone's scraped LinkedIn data on a server with your name on it.

---

## 13. Future UI layer: filter chips (not built yet — planned)

The primary and only search interface is the conversational input box (section 5) — a person can type a bare keyword or a full Darija/French/Arabic/English sentence and it goes through the same `language.py` → `matching.py` pipeline either way. There is no separate "input-field search."

Later, once the core pipeline is solid, add **quick filter chips/dropdowns** as a secondary UI layer for people who prefer clicking over typing:

- **Scope** (Local/International) → `Job.scope`
- **Remote only** → `Job.is_remote`
- **Country** → `Job.country` (International mode only)
- **Seniority** (junior/mid/senior) → not yet a schema field; requires an ingestion-time enrichment step (regex or LLM tag on the description), same pattern as the `is_remote`/`visa_sponsorship` enrichment in section 6
- **Source** (optional) → `Job.source`

A chip never becomes a second search path — clicking one just pre-fills/overrides a field in the same structured query object `language.py` produces (`role_keywords`, `location_scope`, `remote_only`, `seniority`), which then hits `matching.py` exactly as a typed sentence would. This requires no new backend logic beyond the seniority enrichment step — it's a frontend-only addition when you get to it.
