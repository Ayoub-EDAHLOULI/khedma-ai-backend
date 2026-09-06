"""
SQLAlchemy models matching the data model in docs/job-agent-documentation.md (section 4).
Uses pgvector for embedding similarity search — run `CREATE EXTENSION IF NOT EXISTS vector;`
once on your Postgres database before creating these tables.
"""
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)  # 'adzuna' | 'arbeitnow' | 'linkedin' | 'indeed' | 'rekrute' | ...
    source_job_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String)
    country = Column(String)  # ISO country code
    city = Column(String)
    is_remote = Column(Boolean, default=False)
    visa_sponsorship = Column(Boolean, nullable=True)
    scope = Column(String)  # 'local' | 'international'
    description = Column(Text)
    raw_json = Column(JSONB)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), default=utcnow)
    embedding = Column(Vector(1536), nullable=True)

    matches = relationship("Match", back_populates="job")

    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_job_source"),
        CheckConstraint("scope in ('local','international')", name="ck_job_scope"),
    )


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String)
    base_country = Column(String)
    cv_text = Column(Text)
    skills = Column(ARRAY(String), default=list)
    preferred_languages = Column(ARRAY(String), default=list)  # ['darija','fr','ar','en']
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    matches = relationship("Match", back_populates="profile")


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    score = Column(Numeric)
    reasoning = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    job = relationship("Job", back_populates="matches")
    profile = relationship("Profile", back_populates="matches")
    application = relationship("Application", back_populates="match", uselist=False)

    __table_args__ = (UniqueConstraint("job_id", "profile_id", name="uq_match_job_profile"),)


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"))
    tailored_cv = Column(Text)
    cover_letter = Column(Text)
    status = Column(String, default="draft")  # draft | applied | rejected | interview
    created_at = Column(DateTime(timezone=True), default=utcnow)

    match = relationship("Match", back_populates="application")
