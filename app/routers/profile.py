from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.response import ApiResponse
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=ApiResponse[ProfileOut])
def upsert_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    profile = db.scalars(select(Profile).limit(1)).first()

    if profile is None:
        profile = Profile()
        db.add(profile)

    profile.full_name = payload.full_name
    profile.base_country = payload.base_country
    profile.cv_text = payload.cv_text
    profile.skills = payload.skills
    profile.preferred_languages = payload.preferred_languages

    db.commit()
    db.refresh(profile)

    return ApiResponse.ok(ProfileOut.model_validate(profile), "Profile saved")


@router.get("", response_model=ApiResponse[ProfileOut])
def get_profile(db: Session = Depends(get_db)):
    profile = db.scalars(select(Profile).limit(1)).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile found")

    return ApiResponse.ok(ProfileOut.model_validate(profile), "Profile retrieved")
