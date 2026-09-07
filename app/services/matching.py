import json

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, Profile

SHORTLIST_SIZE = 30
TOP_RESULTS = 5
RERANK_MODEL = "gpt-4o-mini"

_client = OpenAI(api_key=settings.openai_api_key)


def shortlist_jobs(
    db: Session,
    profile: Profile,
    scope: str,
    limit: int = SHORTLIST_SIZE,
    remote_only: bool = False,
    country: str | None = None,
    seniority: str | None = None,
) -> list[Job]:
    if profile.embedding is None:
        return []

    conditions = [Job.embedding.isnot(None), Job.scope == scope]
    if remote_only:
        conditions.append(Job.is_remote.is_(True))
    if country:
        conditions.append(Job.country == country)
    if seniority:
        conditions.append(Job.seniority == seniority)

    stmt = (
        select(Job)
        .where(*conditions)
        .order_by(Job.embedding.cosine_distance(profile.embedding))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def rerank_jobs(profile: Profile, jobs: list[Job]) -> list[dict]:
    """Ask the LLM to score 0-100 and give a one-line reason per job (section 7 step 4)."""
    if not jobs:
        return []

    job_summaries = [
        {
            "id": str(job.id),
            "title": job.title,
            "company": job.company,
            "description": (job.description or "")[:1000],
        }
        for job in jobs
    ]

    system_prompt = (
        "You are a job-matching assistant. Given a candidate's profile and a list of "
        "job postings, score each job from 0 to 100 on how well it fits the candidate, "
        "and give a one-line reason. Respond ONLY with a JSON object: "
        '{"results": [{"id": "<job id>", "score": <0-100>, "reasoning": "<one line>"}]}. '
        "Include every job id exactly once."
    )
    user_prompt = json.dumps(
        {
            "candidate": {
                "cv_text": profile.cv_text,
                "skills": profile.skills,
            },
            "jobs": job_summaries,
        }
    )

    response = _client.chat.completions.create(
        model=RERANK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content
    return json.loads(content)["results"]


def find_matches(
    db: Session,
    profile: Profile,
    scope: str,
    remote_only: bool = False,
    country: str | None = None,
    seniority: str | None = None,
) -> list[dict]:
    shortlist = shortlist_jobs(
        db,
        profile,
        scope,
        remote_only=remote_only,
        country=country,
        seniority=seniority,
    )
    ranked = rerank_jobs(profile, shortlist)

    jobs_by_id = {str(job.id): job for job in shortlist}
    results = []
    for entry in ranked:
        job = jobs_by_id.get(entry["id"])
        if job is None:
            continue
        results.append({"job": job, "score": entry["score"], "reasoning": entry["reasoning"]})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:TOP_RESULTS]
