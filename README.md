# Khedma.ai — Backend

**The API behind Khedma.ai** — a multilingual AI job-search agent. Chat in Darija, French, Arabic, or English; get AI-ranked job matches, scoped to your own country or filtered to remote/visa-sponsored international roles; generate a tailored CV and cover letter per posting.

> This is a self-hosted personal tool, not a hosted service — you run your own instance with your own database and API keys. See [Legal & scraping disclaimer](#legal--scraping-disclaimer) before enabling the scraper module.

Frontend repo: [khedma-ai-frontend](#) _(link once created)_ · Mobile: planned, see [Roadmap](#roadmap).

---

## What it does

- 🗣️ **Multilingual chat search** — one endpoint detects Darija (Latin or Arabic script), French, Arabic, or English and replies in the same language.
- 🌍 **Local vs. international scoping** — "local" returns jobs in your own country; "international" filters to remote or visa-sponsored roles only, so results are things you can actually apply to.
- 🎯 **Two-stage AI matching** — pgvector similarity search for a shortlist, then an LLM re-rank for a precise score + one-line reasoning per job.
- 📄 **Tailored application generation** — a rewritten CV summary and a cover letter per job, generated from your real CV text and the job description (never fabricates experience).
- 🔌 **Pluggable job sources** — legitimate free APIs (Adzuna, Arbeitnow) where they have coverage, plus a personal scraper module (LinkedIn, Rekrute, and other Moroccan boards) where they don't.

## Tech stack

FastAPI · PostgreSQL + pgvector · SQLAlchemy · Claude API (or swap in any LLM) · Playwright/httpx for the scraper module

Full architecture, data model, and design rationale: [`docs/job-agent-documentation.md`](docs/job-agent-documentation.md).

## Getting started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with the `pgvector` extension available
- An Anthropic API key (or another LLM provider — see `app/services/`)

### Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # fill in DATABASE_URL, ANTHROPIC_API_KEY, etc.
```

In `psql`, once, on your database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Run it:

```bash
uvicorn app.main:app --reload
```

- Health check: `http://localhost:8000/health`
- Interactive API docs (Swagger): `http://localhost:8000/docs`

## Project structure

```
app/
├── main.py                      FastAPI entrypoint
├── config.py                    settings loaded from .env
├── database.py                  SQLAlchemy engine/session
├── models.py                    Job, Profile, Match, Application tables
├── schemas.py                   Pydantic request/response models
├── routers/
│   ├── profile.py                POST /profile
│   ├── jobs.py                   GET  /jobs/{id}
│   ├── search.py                 POST /search  (multilingual chat search)
│   ├── matches.py                POST /matches/{id}/prepare
│   └── applications.py           GET/PATCH /applications
└── services/
    ├── language.py               multilingual query extraction
    ├── matching.py                embedding search + LLM re-rank
    ├── application_writer.py      tailored CV + cover letter generation
    └── sources/                   pluggable job data sources
        ├── base.py                 JobSource interface
        ├── adzuna.py                Adzuna API
        ├── arbeitnow.py             Arbeitnow API
        ├── scraper_linkedin.py      personal LinkedIn scraper
        └── scraper_rekrute.py       personal Rekrute.com scraper
```

## Data sources

| Module  | Sources                                             | Notes                                               |
| ------- | --------------------------------------------------- | --------------------------------------------------- |
| API     | Adzuna, Arbeitnow                                   | Free, legal, zero maintenance — no Morocco coverage |
| Scraper | LinkedIn, Rekrute (Indeed/Emploi.ma/ANAPEC planned) | Personal use only — see disclaimer below            |

Add a new source by implementing `JobSource` in `app/services/sources/base.py`.

## Legal & scraping disclaimer

The scraper module reads publicly visible listings from sites including LinkedIn. Before enabling it:

- **Scraping likely violates those sites' Terms of Service.** It is not illegal to scrape public data under U.S. law (_hiQ Labs v. LinkedIn_), but ToS violations are a civil/contractual matter — the practical risk is your account or IP being rate-limited or banned.
- **This is built for one person running it on their own account/IP for their own job search** — not to be centralized or operated as a service for other users. Doing so changes the risk profile significantly (see `docs/job-agent-documentation.md`, section 2a).
- **You're responsible for how you use this software.** No guarantee the scrapers keep working as target sites change their markup.
- **Not affiliated with, endorsed by, or connected to** LinkedIn, Indeed, Rekrute, or any other referenced job board.
- Default scraper delays (`SCRAPER_MIN_DELAY_SECONDS` / `SCRAPER_MAX_DELAY_SECONDS`) are intentionally conservative — please don't lower them.

Same posture as other open-source job scrapers, e.g. [JobSpy](https://github.com/speedyapply/JobSpy).

## Roadmap

- [x] Core data model + API skeleton
- [ ] Full source coverage (Indeed, Emploi.ma, ANAPEC, Bayt)
- [ ] Frontend ([khedma-ai-frontend](#)) consuming this API
- [ ] Mobile app — same API, self-hosted per user
- [ ] Mock interview simulation based on the job applied to

## Contributing

Issues and PRs welcome. New job sources should implement `JobSource` and keep scraper-based sources rate-limit-friendly by default.

## License

MIT — see [LICENSE](LICENSE).
