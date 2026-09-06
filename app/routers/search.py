from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
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

    matches = find_matches(db, profile, scope=scope)

    result = SearchResponse(
        detected_language=query["detected_language"],
        reply=f"Found {len(matches)} matching jobs.",
        results=[
            SearchResultItem(
                job=JobOut.model_validate(m["job"]),
                score=m["score"],
                reasoning=m["reasoning"],
            )
            for m in matches
        ],
    )
    return ApiResponse.ok(result, "Search complete")
