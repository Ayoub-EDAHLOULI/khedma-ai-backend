"""
Standalone ingestion entrypoint. Not an HTTP endpoint (see docs section 9) —
run directly, e.g.:

    python -m app.services.sources.ingest
"""
import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Job, Profile
from app.services.embeddings import embed_texts
from app.services.sources.adzuna import AdzunaSource
from app.services.sources.arbeitnow import ArbeitnowSource
from app.services.sources.base import JobSource, NormalizedJob
from app.services.sources.jsearch import JSearchSource
from app.services.sources.scraper_anapec import AnapecSource
from app.services.sources.scraper_indeed import IndeedSource
from app.services.sources.scraper_rekrute import RekruteSource

SOURCES: list[JobSource] = [
    ArbeitnowSource(),
    AdzunaSource(),
    JSearchSource(),
    RekruteSource(),
    AnapecSource(),
    IndeedSource(),
]


def upsert_job(db, job: NormalizedJob) -> None:
    stmt = insert(Job).values(
        source=job.source,
        source_job_id=job.source_job_id,
        title=job.title,
        company=job.company,
        country=job.country,
        city=job.city,
        is_remote=job.is_remote,
        visa_sponsorship=job.visa_sponsorship,
        description=job.description,
        url=job.url,
        posted_at=job.posted_at,
        raw_json=job.raw_json,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_job_id"],
        set_={
            "title": stmt.excluded.title,
            "company": stmt.excluded.company,
            "country": stmt.excluded.country,
            "city": stmt.excluded.city,
            "is_remote": stmt.excluded.is_remote,
            "visa_sponsorship": stmt.excluded.visa_sponsorship,
            "description": stmt.excluded.description,
            "url": stmt.excluded.url,
            "posted_at": stmt.excluded.posted_at,
            "raw_json": stmt.excluded.raw_json,
        },
    )
    db.execute(stmt)


def classify_scope(job: Job, profile: Profile) -> str:
    """Section 6: local/international/discard classification."""
    if job.country and profile.base_country and job.country == profile.base_country:
        return "local"

    if (
        job.is_remote
        or job.visa_sponsorship
        or (job.country and job.country in (profile.target_countries or []))
    ):
        return "international"

    return "discard"


SENIOR_PATTERN = re.compile(
    r"\b(senior|sr\.?|lead|principal|staff|head of|director|architect)\b", re.IGNORECASE
)
JUNIOR_PATTERN = re.compile(
    r"\b(junior|jr\.?|intern(ship)?|entry.level|graduate|apprentice)\b", re.IGNORECASE
)


def classify_seniority(job: Job) -> str | None:
    """Keyword-based seniority tag from the title (most reliable signal), falling
    back to the description. Same enrichment pattern as classify_scope — best-effort,
    not exhaustive; jobs that match nothing stay unclassified (None) rather than
    guessing "mid" by default."""
    haystacks = [job.title or "", (job.description or "")[:500]]
    for text_ in haystacks:
        if SENIOR_PATTERN.search(text_):
            return "senior"
        if JUNIOR_PATTERN.search(text_):
            return "junior"
    return "mid" if job.title else None


def classify_pending_jobs(db) -> int:
    profile = db.scalars(select(Profile).limit(1)).first()
    if profile is None:
        print("scope classification skipped: no profile found")
        return 0

    pending = db.scalars(select(Job).where(Job.scope.is_(None))).all()
    for job in pending:
        job.scope = classify_scope(job, profile)
    db.commit()

    return len(pending)


def classify_pending_seniority(db) -> int:
    pending = db.scalars(select(Job).where(Job.seniority.is_(None))).all()
    for job in pending:
        job.seniority = classify_seniority(job)
    db.commit()

    return len(pending)


def embed_pending_jobs(db, batch_size: int = 100) -> int:
    pending = db.scalars(
        select(Job).where(
            Job.embedding.is_(None),
            Job.description.isnot(None),
            Job.scope != "discard",
        )
    ).all()

    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        vectors = embed_texts([job.description for job in batch])
        for job, vector in zip(batch, vectors):
            job.embedding = vector
        db.commit()

    return len(pending)


def get_queries_from_profile(db) -> list[str] | None:
    """Query-driven sources (JSearch, Indeed) search using the profile's own skills,
    so ingestion pulls jobs relevant to whoever is actually running this instance —
    a .NET/React profile pulls .NET/React jobs, an HR profile pulls HR jobs, etc.
    Falls back to each source's own generic default if no profile/skills exist yet.
    """
    profile = db.scalars(select(Profile).limit(1)).first()
    if profile is None or not profile.skills:
        return None
    return profile.skills


def run() -> None:
    db = SessionLocal()
    try:
        queries = get_queries_from_profile(db)

        for source in SOURCES:
            jobs = source.fetch(queries=queries)
            print(f"{source.name}: fetched {len(jobs)} jobs")
            for job in jobs:
                upsert_job(db, job)
            db.commit()

        classified_count = classify_pending_jobs(db)
        print(f"classified {classified_count} jobs")

        seniority_count = classify_pending_seniority(db)
        print(f"classified seniority for {seniority_count} jobs")

        embedded_count = embed_pending_jobs(db)
        print(f"embedded {embedded_count} jobs")
    finally:
        db.close()


if __name__ == "__main__":
    run()
