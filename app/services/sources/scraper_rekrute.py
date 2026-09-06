import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.services.sources.base import JobSource, NormalizedJob

BASE_URL = "https://www.rekrute.com"
LISTING_URL = f"{BASE_URL}/offres.html"
RESULTS_PER_PAGE = 50  # s=3 in Rekrute's own pagination
MAX_PAGES = 5
REQUEST_DELAY_SECONDS = settings.scraper_min_delay_seconds

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DATE_RANGE_RE = re.compile(r"du\s+(\d{2}/\d{2}/\d{4})")


class RekruteSource(JobSource):
    name = "rekrute"

    def fetch(self) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []

        with requests.Session() as client:
            client.headers.update({"User-Agent": USER_AGENT})
            for page in range(1, MAX_PAGES + 1):
                response = client.get(LISTING_URL, params={"s": 3, "p": page, "o": 1}, timeout=15.0)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                job_list = soup.find("ul", class_="job-list")
                if job_list is None:
                    break

                items = job_list.find_all("li", recursive=False)
                if not items:
                    break

                for item in items:
                    job = self._parse_item(item)
                    if job is not None:
                        jobs.append(job)

                time.sleep(REQUEST_DELAY_SECONDS)

        return jobs

    def _parse_item(self, item) -> NormalizedJob | None:
        post_id = item.get("id")
        title_a = item.find("a", class_="titreJob")
        if post_id is None or title_a is None:
            return None

        raw_title = title_a.get_text(strip=True)
        title, _, city_part = raw_title.partition("|")
        title = title.strip()
        city = city_part.replace("(Maroc)", "").strip() or None

        detail_url = BASE_URL + title_a["href"] if title_a.get("href", "").startswith("/") else title_a.get("href")

        img = item.find("img", class_="photo")
        company = img.get("title") if img else None

        date_em = item.find("em", class_="date")
        posted_at = None
        if date_em:
            match = DATE_RANGE_RE.search(date_em.get_text(" ", strip=True))
            if match:
                posted_at = datetime.strptime(match.group(1), "%d/%m/%Y").replace(tzinfo=timezone.utc)

        description_span = item.select_one(".info span")
        description = description_span.get_text(strip=True) if description_span else None

        return NormalizedJob(
            source=self.name,
            source_job_id=post_id,
            title=title,
            company=company,
            country="MA",
            city=city,
            is_remote=False,
            description=description,
            posted_at=posted_at,
            raw_json={"detail_url": detail_url},
        )
