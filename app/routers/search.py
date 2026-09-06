from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.response import ApiResponse
from app.schemas import JobOut, SearchRequest, SearchResponse, SearchResultItem
from app.services.matching import find_matches

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=ApiResponse[SearchResponse])
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    profile = db.get(Profile, payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # TODO: replace with app.services.language once built — for now scope comes
    # directly from the request instead of being extracted from `message`.
    matches = find_matches(db, profile, scope=payload.scope)

    result = SearchResponse(
        detected_language="en",
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
