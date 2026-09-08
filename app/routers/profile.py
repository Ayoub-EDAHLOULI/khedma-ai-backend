import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.response import ApiResponse
from app.schemas import ParsedResumeResponse, ProfileIn, ProfileOut
from app.services.embeddings import embed_text
from app.services.resume_parser import (
    NotAResumeError,
    UnsupportedFileTypeError,
    parse_resume,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=ApiResponse[ProfileOut])
def upsert_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    profile = db.scalars(select(Profile).limit(1)).first()

    if profile is None:
        profile = Profile()
        db.add(profile)

    profile.full_name = payload.full_name
    profile.base_country = payload.base_country
    profile.target_countries = payload.target_countries
    profile.cv_text = payload.cv_text
    profile.skills = payload.skills
    profile.preferred_languages = payload.preferred_languages

    if payload.resume_docx is not None:
        profile.resume_docx = base64.b64decode(payload.resume_docx)
        profile.resume_filename = payload.resume_filename

    embedding_input = payload.cv_text + "\n" + ", ".join(payload.skills)
    profile.embedding = embed_text(embedding_input)

    db.commit()
    db.refresh(profile)

    return ApiResponse.ok(ProfileOut.model_validate(profile), "Profile saved")


@router.get("", response_model=ApiResponse[ProfileOut])
def get_profile(db: Session = Depends(get_db)):
    profile = db.scalars(select(Profile).limit(1)).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile found")

    return ApiResponse.ok(ProfileOut.model_validate(profile), "Profile retrieved")


@router.post("/parse-resume", response_model=ApiResponse[ParsedResumeResponse])
async def parse_resume_upload(file: UploadFile):
    content = await file.read()

    try:
        result = parse_resume(file.filename or "", content)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotAResumeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ApiResponse.ok(ParsedResumeResponse(**result), "Resume parsed")
