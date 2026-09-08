from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Match
from app.response import ApiResponse
from app.schemas import PrepareResponse
from app.services.application_writer import write_application

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/{match_id}/prepare", response_model=ApiResponse[PrepareResponse])
def prepare_application(match_id: UUID, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    existing = db.scalars(
        select(Application).where(Application.match_id == match_id)
    ).first()
    if existing is not None:
        return ApiResponse.ok(
            PrepareResponse(
                id=existing.id,
                status=existing.status,
                tailored_cv=existing.tailored_cv,
                cover_letter=existing.cover_letter,
            ),
            "Application package already prepared",
        )

    result = write_application(match.profile, match.job)
    tailored_cv = result["tailored_cv"]
    cover_letter = result["cover_letter"]

    application = Application(
        match_id=match.id,
        tailored_cv=tailored_cv,
        cover_letter=cover_letter,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return ApiResponse.ok(
        PrepareResponse(
            id=application.id,
            status=application.status,
            tailored_cv=tailored_cv,
            cover_letter=cover_letter,
        ),
        "Application package prepared",
    )
