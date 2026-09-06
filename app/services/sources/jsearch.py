from datetime import datetime, timezone

import requests

from app.config import settings
from app.services.sources.base import JobSource, NormalizedJob

API_URL = "https://jsearch.p.rapidapi.com/search-v2"

# Free tier is capped at 200 requests/month — keep this list short.
QUERIES = [
    "software engineer remote",
    "developer",
]


class JSearchSource(JobSource):
    name = "jsearch"

    def fetch(self) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
            "x-rapidapi-key": settings.jsearch_rapidapi_key,
        }

        with requests.Session() as client:
            client.headers.update(headers)
            for query in QUERIES:
                params = {"query": query, "num_pages": "1", "date_posted": "all"}
                response = client.get(API_URL, params=params, timeout=20.0)
                response.raise_for_status()
                payload = response.json()

                for entry in payload.get("data", {}).get("jobs", []):
                    jobs.append(self._normalize(entry))

        return jobs

    def _normalize(self, entry: dict) -> NormalizedJob:
        posted_at = None
        if entry.get("job_posted_at_datetime_utc"):
            posted_at = datetime.fromisoformat(
                entry["job_posted_at_datetime_utc"].replace("Z", "+00:00")
            )

        return NormalizedJob(
            source=self.name,
            source_job_id=entry["job_id"],
            title=entry["job_title"],
            company=entry.get("employer_name"),
            country=entry.get("job_country"),
            city=entry.get("job_city"),
            is_remote=bool(entry.get("job_is_remote", False)),
            description=entry.get("job_description"),
            posted_at=posted_at,
            raw_json=entry,
        )
