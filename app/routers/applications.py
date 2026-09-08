from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Application, Match
from app.response import ApiResponse
from app.schemas import ApplicationOut, ApplicationStatusUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=ApiResponse[list[ApplicationOut]])
def list_applications(db: Session = Depends(get_db)):
    applications = db.scalars(
        select(Application)
        .options(joinedload(Application.match).joinedload(Match.job))
        .order_by(Application.created_at.desc())
    ).all()
    data = [ApplicationOut.from_application(a) for a in applications]
    return ApiResponse.ok(data, "Applications retrieved")


@router.patch("/{application_id}", response_model=ApiResponse[ApplicationOut])
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = payload.status
    db.commit()
    db.refresh(application)

    return ApiResponse.ok(ApplicationOut.from_application(application), "Application updated")
