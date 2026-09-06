"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileIn(BaseModel):
    full_name: str
    base_country: str
    cv_text: str
    skills: list[str] = []
    preferred_languages: list[str] = ["darija", "fr", "ar", "en"]


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


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
    description: Optional[str] = None


class SearchRequest(BaseModel):
    message: str
    profile_id: UUID


class SearchResultItem(BaseModel):
    job: JobOut
    score: float
    reasoning: str


class SearchResponse(BaseModel):
    detected_language: str
    reply: str
    results: list[SearchResultItem]


class PrepareResponse(BaseModel):
    tailored_cv: str
    cover_letter: str
