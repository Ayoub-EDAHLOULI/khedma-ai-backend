from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match, Profile
from app.response import ApiResponse
from app.schemas import JobOut, SearchRequest, SearchResponse, SearchResultItem
from app.services.language import extract_query
from app.services.matching import find_matches

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=ApiResponse[SearchResponse])
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    profile = db.get(Profile, payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    query = extract_query(payload.message)
    scope = payload.scope or query["location_scope"]

    if scope is None:
        result = SearchResponse(
            detected_language=query["detected_language"],
            reply=query["clarifying_question"],
            results=[],
        )
        return ApiResponse.ok(result, "Clarification needed")

    # Explicit chip selections win; otherwise fall back to whatever the LLM
    # picked up from the message itself (e.g. spoken "junior jobs in the UK").
    remote_only = payload.remote_only if payload.remote_only is not None else bool(query.get("remote_only"))

    country = payload.country or query.get("country")
    if not (isinstance(country, str) and len(country) == 2):
        country = None
    elif payload.country is None:
        country = country.upper()

    seniority = payload.seniority or query.get("seniority")
    if seniority not in ("junior", "mid", "senior"):
        seniority = None

    matches = find_matches(
        db,
        profile,
        scope=scope,
        remote_only=remote_only,
        country=country,
        seniority=seniority,
    )

    results = []
    for m in matches:
        stmt = (
            insert(Match)
            .values(job_id=m["job"].id, profile_id=profile.id, score=m["score"], reasoning=m["reasoning"])
            .on_conflict_do_update(
                index_elements=["job_id", "profile_id"],
                set_={"score": m["score"], "reasoning": m["reasoning"]},
            )
            .returning(Match.id)
        )
        match_id = db.execute(stmt).scalar_one()
        results.append(
            SearchResultItem(
                match_id=match_id,
                job=JobOut.model_validate(m["job"]),
                score=m["score"],
                reasoning=m["reasoning"],
            )
        )
    db.commit()

    result = SearchResponse(
        detected_language=query["detected_language"],
        reply=f"Found {len(matches)} matching jobs.",
        results=results,
    )
    return ApiResponse.ok(result, "Search complete")
