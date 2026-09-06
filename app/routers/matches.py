from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Match
from app.response import ApiResponse
from app.schemas import PrepareResponse

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/{match_id}/prepare", response_model=ApiResponse[PrepareResponse])
def prepare_application(match_id: UUID, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    # TODO: replace with app.services.application_writer once the LLM call is wired up.
    tailored_cv = ""
    cover_letter = ""

    application = Application(
        match_id=match.id,
        tailored_cv=tailored_cv,
        cover_letter=cover_letter,
    )
    db.add(application)
    db.commit()

    return ApiResponse.ok(
        PrepareResponse(tailored_cv=tailored_cv, cover_letter=cover_letter),
        "Application package prepared",
    )
