"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProfileIn(BaseModel):
    full_name: str
    base_country: str
    target_countries: list[str] = []
    cv_text: str
    skills: list[str] = []
    preferred_languages: list[str] = ["darija", "fr", "ar", "en"]
    resume_docx: Optional[str] = None  # base64; omit to leave any stored file unchanged
    resume_filename: Optional[str] = None


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class ParsedResumeResponse(BaseModel):
    full_name: str
    skills: list[str] = []
    cv_text: str
    resume_docx: Optional[str] = None  # base64, only when the upload was a .docx
    resume_filename: Optional[str] = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    title: str
    company: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    is_remote: bool
    scope: Optional[str] = None
    seniority: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class SearchRequest(BaseModel):
    message: str
    profile_id: UUID
    scope: Optional[Literal["local", "international"]] = None
    remote_only: Optional[bool] = None
    country: Optional[str] = None
    seniority: Optional[Literal["junior", "mid", "senior"]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=30)


class SearchResultItem(BaseModel):
    match_id: UUID
    job: JobOut
    score: float
    reasoning: str


class SearchResponse(BaseModel):
    detected_language: str
    reply: str
    results: list[SearchResultItem]


class PrepareResponse(BaseModel):
    id: UUID
    status: str
    tailored_cv: str
    cover_letter: str


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    match_id: UUID
    job: JobOut
    score: float
    tailored_cv: Optional[str] = None
    cover_letter: Optional[str] = None
    status: str
    created_at: datetime

    @classmethod
    def from_application(cls, application):
        return cls(
            id=application.id,
            match_id=application.match_id,
            job=JobOut.model_validate(application.match.job),
            score=application.match.score,
            tailored_cv=application.tailored_cv,
            cover_letter=application.cover_letter,
            status=application.status,
            created_at=application.created_at,
        )


class ApplicationStatusUpdate(BaseModel):
    status: Literal["draft", "applied", "rejected", "interview"]


class VoiceSessionTokenResponse(BaseModel):
    token: str
    model: str
    expire_time: datetime
