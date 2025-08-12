"""Pydantic schemas for proposal sections & drafting.

These are the typed contracts between the frontend and backend for:
- Section instruction sheets (what to write + how to write it)
- Draft requests and responses (full HTML plus checks & sources)
"""
from __future__ import annotations

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


# ---------------------------
# Instruction Sheet Schema
# ---------------------------

class LengthHint(BaseModel):
    min: int
    max: int


class SectionInstruction(BaseModel):
    section_key: str
    title: str
    purpose: str
    must_include: List[str]
    micro_outline: List[str]
    tone_rules: List[str]
    win_themes: List[str]
    evidence_prompts: List[str]
    compliance_checklist: List[str]
    length_hint_words: LengthHint
    acceptance_criteria: List[str]
    gaps: List[str] = Field(default_factory=list)


class OutlineItem(BaseModel):
    title: str
    key: Optional[str] = None


class GenerateInstructionsReq(BaseModel):
    outline: List[OutlineItem]
    use_knowledge_base: bool = False


# ---------------------------
# Drafting Request/Response
# ---------------------------

class SourceAttribution(BaseModel):
    id: str
    kind: Literal["RFP", "KB", "EX"]
    meta: Dict[str, str] = Field(default_factory=dict)


class DraftReq(BaseModel):
    instruction: SectionInstruction
    example_ids: Optional[List[str]] = None
    filters: Optional[Dict[str, str]] = None
    use_knowledge_base: bool = False


class DraftResp(BaseModel):
    html: str
    sources: List[SourceAttribution]
    checks: Dict[str, object]
