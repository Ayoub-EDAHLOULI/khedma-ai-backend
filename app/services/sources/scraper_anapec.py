import time
import warnings
from datetime import datetime, timezone

import requests
import urllib3
from bs4 import BeautifulSoup

from app.config import settings
from app.services.sources.base import JobSource, NormalizedJob

# anapec.org serves an incomplete certificate chain (missing intermediate cert) —
# browsers tolerate it via a cached intermediate, Python's strict verification does not.
# This is a misconfiguration on their end, not a MITM concern for a public government
# job board we're intentionally reading, so verification is disabled for this host only.
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.anapec.org"
LISTING_URL_TEMPLATE = (
    f"{BASE_URL}/sigec-app-rv/chercheurs/resultat_recherche/page:{{page}}/tout:all/language:fr"
)
MAX_PAGES = 10
REQUEST_DELAY_SECONDS = settings.scraper_min_delay_seconds

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class AnapecSource(JobSource):
    name = "anapec"

    def fetch(self, queries: list[str] | None = None) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []

        with requests.Session() as client:
            client.headers.update({"User-Agent": USER_AGENT})
            for page in range(1, MAX_PAGES + 1):
                url = LISTING_URL_TEMPLATE.format(page=page)
                response = client.get(url, timeout=15.0, verify=False)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.find("table", id="myTable")
                if table is None:
                    break

                rows = table.find_all("tr")[1:]  # skip header row
                if not rows:
                    break

                for row in rows:
                    job = self._parse_row(row)
                    if job is not None:
                        jobs.append(job)

                time.sleep(REQUEST_DELAY_SECONDS)

        return jobs

    def _parse_row(self, row) -> NormalizedJob | None:
        cells = row.find_all("td")
        if len(cells) < 7:
            return None

        ref_link = cells[1].find("a")
        if ref_link is None:
            return None

        reference = ref_link.get_text(strip=True)
        href = ref_link.get("href", "")
        offer_id = href.rstrip("/").split("/")[-2] if "bloc_offre_home" in href else reference
        detail_url = BASE_URL + href if href.startswith("/") else (href or None)

        date_text = cells[2].get_text(strip=True)
        posted_at = None
        if date_text:
            try:
                posted_at = datetime.strptime(date_text, "%d/%m/%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                posted_at = None

        title = cells[3].get_text(strip=True)
        company = cells[5].get_text(strip=True)
        company = None if company in ("-", "") else company
        city = cells[6].get_text(strip=True) or None

        return NormalizedJob(
            source=self.name,
            source_job_id=offer_id,
            title=title,
            company=company,
            country="MA",
            city=city,
            is_remote=False,
            description=None,
            url=detail_url,
            posted_at=posted_at,
            raw_json={"reference": reference},
        )
