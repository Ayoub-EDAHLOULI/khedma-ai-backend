from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.response import ApiResponse
from app.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=ApiResponse[SearchResponse])
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    # TODO: replace with app.services.language (detect + extract) and
    # app.services.matching (pgvector shortlist + LLM re-rank) once built.
    result = SearchResponse(
        detected_language="en",
        reply="Search is not wired up yet.",
        results=[],
    )
    return ApiResponse.ok(result, "Search complete")
