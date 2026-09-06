import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from app.config import settings
from app.services.sources.base import JobSource, NormalizedJob

BASE_URL = "https://www.indeed.com/jobs"
JOBCARDS_MARKER = '["mosaic-provider-jobcards"]='
REQUEST_DELAY_SECONDS = settings.scraper_min_delay_seconds

# Playwright + a real browser avoids the 403s a plain HTTP client gets after a
# couple of requests (confirmed live) — still real anti-bot risk on repeated
# use, so keep queries few and delays conservative (section 12).
# Used only if no queries are given.
DEFAULT_QUERIES = ["software engineer remote", "python developer"]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

TAG_RE = re.compile(r"<[^>]+>")


class IndeedSource(JobSource):
    name = "indeed"

    def fetch(self, queries: list[str] | None = None) -> list[NormalizedJob]:
        queries = queries or DEFAULT_QUERIES
        jobs: list[NormalizedJob] = []

        # Indeed's bot detection triggers a "Security Check" challenge on a second
        # navigation within the same browser session (confirmed live) — a fresh
        # browser per query avoids that, at the cost of extra startup time per query.
        with sync_playwright() as p:
            for i, query in enumerate(queries):
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(f"{BASE_URL}?q={quote(query)}", timeout=30000)
                html = page.content()
                browser.close()

                for entry in self._extract_results(html):
                    jobs.append(self._normalize(entry))

                if i < len(queries) - 1:
                    time.sleep(REQUEST_DELAY_SECONDS)

        return jobs

    def _extract_results(self, html: str) -> list[dict]:
        idx = html.find(JOBCARDS_MARKER)
        if idx == -1:
            return []

        start = idx + len(JOBCARDS_MARKER)
        end = html.find(";\n", start)
        if end == -1:
            return []

        try:
            data = json.loads(html[start:end])
        except json.JSONDecodeError:
            return []

        return data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", [])

    def _normalize(self, entry: dict) -> NormalizedJob:
        description = None
        if entry.get("snippet"):
            description = TAG_RE.sub(" ", entry["snippet"]).strip()

        posted_at = None
        if entry.get("createDate"):
            posted_at = datetime.fromtimestamp(entry["createDate"] / 1000, tz=timezone.utc)

        city = entry.get("jobLocationCity") or entry.get("formattedLocation")

        return NormalizedJob(
            source=self.name,
            source_job_id=entry["jobkey"],
            title=entry.get("displayTitle") or entry.get("title", ""),
            company=entry.get("company"),
            city=city,
            is_remote=bool(entry.get("remoteLocation", False)),
            description=description,
            posted_at=posted_at,
            raw_json=entry,
        )
