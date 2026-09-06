import time
from datetime import datetime, timezone

import requests

from app.services.sources.base import JobSource, NormalizedJob

API_URL = "https://www.arbeitnow.com/api/job-board-api"
REQUEST_DELAY_SECONDS = 3.0
MAX_RETRIES = 5


class ArbeitnowSource(JobSource):
    name = "arbeitnow"

    def fetch(self) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        url = API_URL

        with requests.Session() as client:
            while url:
                payload = self._get_with_retry(client, url)

                for entry in payload["data"]:
                    jobs.append(self._normalize(entry))

                url = payload.get("links", {}).get("next")
                if url:
                    time.sleep(REQUEST_DELAY_SECONDS)

        return jobs

    def _get_with_retry(self, client: requests.Session, url: str) -> dict:
        for attempt in range(MAX_RETRIES):
            response = client.get(url, timeout=10.0)
            if response.status_code == 429:
                wait = REQUEST_DELAY_SECONDS * (2 ** attempt)
                print(f"arbeitnow: rate limited, waiting {wait:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

        raise RuntimeError(f"arbeitnow: giving up on {url} after {MAX_RETRIES} retries")

    def _normalize(self, entry: dict) -> NormalizedJob:
        posted_at = None
        if entry.get("created_at"):
            posted_at = datetime.fromtimestamp(entry["created_at"], tz=timezone.utc)

        return NormalizedJob(
            source=self.name,
            source_job_id=entry["slug"],
            title=entry["title"],
            company=entry.get("company_name"),
            city=entry.get("location"),
            is_remote=bool(entry.get("remote", False)),
            description=entry.get("description"),
            posted_at=posted_at,
            raw_json=entry,
        )
