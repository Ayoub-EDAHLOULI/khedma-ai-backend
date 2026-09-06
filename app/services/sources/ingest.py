"""
Standalone ingestion entrypoint. Not an HTTP endpoint (see docs section 9) —
run directly, e.g.:

    python -m app.services.sources.ingest
"""
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Job
from app.services.sources.adzuna import AdzunaSource
from app.services.sources.arbeitnow import ArbeitnowSource
from app.services.sources.base import JobSource, NormalizedJob
from app.services.sources.jsearch import JSearchSource
from app.services.sources.scraper_anapec import AnapecSource
from app.services.sources.scraper_rekrute import RekruteSource

SOURCES: list[JobSource] = [
    ArbeitnowSource(),
    AdzunaSource(),
    JSearchSource(),
    RekruteSource(),
    AnapecSource(),
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
            "posted_at": stmt.excluded.posted_at,
            "raw_json": stmt.excluded.raw_json,
        },
    )
    db.execute(stmt)


def run() -> None:
    db = SessionLocal()
    try:
        for source in SOURCES:
            jobs = source.fetch()
            print(f"{source.name}: fetched {len(jobs)} jobs")
            for job in jobs:
                upsert_job(db, job)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
