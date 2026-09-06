from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class NormalizedJob:
    source: str
    source_job_id: str
    title: str
    company: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    is_remote: bool = False
    visa_sponsorship: Optional[bool] = None
    description: Optional[str] = None
    posted_at: Optional[datetime] = None
    raw_json: dict[str, Any] = field(default_factory=dict)


class JobSource(ABC):
    name: str

    @abstractmethod
    def fetch(self, queries: list[str] | None = None) -> list[NormalizedJob]:
        """Fetch postings from this source and return them normalized for the `jobs` table.

        `queries` is a list of role/skill search terms (e.g. from a profile's skills,
        or an explicit search request). Sources that don't need a query concept
        (bulk feeds like Arbeitnow, or listing scrapers like Rekrute/ANAPEC) ignore it.
        """
