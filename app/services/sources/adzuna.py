import time
from datetime import datetime

import requests

from app.config import settings
from app.services.sources.base import JobSource, NormalizedJob

API_BASE = "https://api.adzuna.com/v1/api/jobs"
SUPPORTED_COUNTRIES = [
    "at", "au", "be", "br", "ca", "ch", "de", "es", "fr", "gb",
    "in", "it", "mx", "nl", "nz", "pl", "sg", "us", "za",
]
RESULTS_PER_PAGE = 50
PAGES_PER_COUNTRY = 1
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 5

REMOTE_KEYWORDS = ("remote", "work from home", "wfh")
VISA_KEYWORDS = ("visa sponsorship", "visa sponsor", "sponsorship available")


class AdzunaSource(JobSource):
    name = "adzuna"

    def fetch(self, queries: list[str] | None = None) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []

        with requests.Session() as client:
            for country in SUPPORTED_COUNTRIES:
                for page in range(1, PAGES_PER_COUNTRY + 1):
                    payload = self._get_with_retry(client, country, page)
                    for entry in payload.get("results", []):
                        jobs.append(self._normalize(entry, country))
                    time.sleep(REQUEST_DELAY_SECONDS)

        return jobs

    def _get_with_retry(self, client: requests.Session, country: str, page: int) -> dict:
        url = f"{API_BASE}/{country}/search/{page}"
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "results_per_page": RESULTS_PER_PAGE,
        }

        for attempt in range(MAX_RETRIES):
            response = client.get(url, params=params, timeout=10.0)
            if response.status_code == 429:
                wait = REQUEST_DELAY_SECONDS * (2 ** attempt)
                print(f"adzuna: rate limited on {country}, waiting {wait:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

        raise RuntimeError(f"adzuna: giving up on {country} page {page} after {MAX_RETRIES} retries")

    def _normalize(self, entry: dict, country: str) -> NormalizedJob:
        description = entry.get("description", "") or ""
        text = description.lower()

        location = entry.get("location", {})
        area = location.get("area", [])
        city = location.get("display_name")

        posted_at = None
        if entry.get("created"):
            posted_at = datetime.fromisoformat(entry["created"].replace("Z", "+00:00"))

        return NormalizedJob(
            source=self.name,
            source_job_id=str(entry["id"]),
            title=entry["title"],
            company=(entry.get("company") or {}).get("display_name"),
            country=country.upper(),
            city=city,
            is_remote=any(kw in text for kw in REMOTE_KEYWORDS),
            visa_sponsorship=any(kw in text for kw in VISA_KEYWORDS) or None,
            description=description,
            posted_at=posted_at,
            raw_json=entry,
        )
