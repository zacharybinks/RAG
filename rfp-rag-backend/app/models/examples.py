"""SQLAlchemy models for example proposals and section instructions.

These tables back the examples upload/index flow and the instruction
sheets generated per section. We use string UUIDs for portability across
SQLite/Postgres; if you're on Postgres only, you can switch to the
`UUID` type from `sqlalchemy.dialects.postgresql`.
"""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Your project uses a root-level `database.py` that exposes `Base`
from database import Base


class ProposalExample(Base):
    __tablename__ = "proposal_examples"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    title = Column(String, nullable=False)

    # Optional metadata used for filtering/search
    client_type = Column(String)
    domain = Column(String)
    contract_vehicle = Column(String)
    complexity_tier = Column(String)
    tags = Column(JSON)  # arbitrary key/value tags

    source_path = Column(String, nullable=False)
    ingest_status = Column(String, nullable=False, default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sections = relationship(
        "ExampleSection",
        back_populates="example",
        cascade="all, delete-orphan",
    )


class ExampleSection(Base):
    __tablename__ = "example_sections"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    example_id = Column(String, ForeignKey("proposal_examples.id", ondelete="CASCADE"), nullable=False)

    section_key = Column(String, index=True, nullable=False)
    text = Column(Text, nullable=False)

    tokens = Column(Float)
    quality_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship back to parent example
    example = relationship("ProposalExample", back_populates="sections")


class SectionInstructionRow(Base):
    __tablename__ = "section_instructions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, nullable=False)
    section_key = Column(String, nullable=False)
    json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
