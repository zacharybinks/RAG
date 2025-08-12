"""Instruction sheet generator (project-aware).

Creates a structured SectionInstruction JSON for each outline item using:
- project-specific LLM settings (model/temperature)
- light RFP/KB context (passed in as `ctx`)

The result is a strict, machine-usable object the UI can render and the
Draft service can follow deterministically.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from .llm import chat_json_project
from app.schemas.sections import SectionInstruction

# System guidance for government proposal style
INSTRUCTION_SYSTEM = (
    "You are a senior proposal manager for US Government proposals. "
    "Return only valid JSON for a SectionInstruction as per schema. "
    "Use context excerpts to tailor must-include items and compliance cues. Avoid pricing."
)

# Prompt template used to create the instruction JSON
TEMPLATE = """
Generate a Section Instruction Sheet.
Keys: section_key, title, purpose, must_include, micro_outline, tone_rules, win_themes, evidence_prompts, compliance_checklist, length_hint_words, acceptance_criteria, gaps.
Section title: {title}
Canonical key (if provided): {key}
Context excerpts:
{context}
"""

# Default tone rules if the model does not populate them explicitly
DEFAULT_TONE = [
    "formal plain-language",
    "active voice",
    "no colloquialisms",
    "evidence-led",
    "FAR-aware",
]


def build_instruction(
    project_id: str,
    title: str,
    key: Optional[str],
    ctx: List[str],
    db: Session,
) -> SectionInstruction:
    """Create a SectionInstruction for a single outline item.

    Args:
        project_id: External string ID of the project (not the DB PK).
        title: Human-facing section title from the outline.
        key: Optional canonical key (snake_case). If absent, derived from title.
        ctx: Short list of RFP/KB snippets to tailor guidance.
        db: SQLAlchemy session (used to resolve per-project LLM settings).

    Returns:
        SectionInstruction pydantic object with strict fields.
    """
    # Join context snippets with blank lines; safe on empty lists
    ctx_text = "\n\n".join(ctx[:8]) or ""

    data = chat_json_project(
        project_id=project_id,
        system=INSTRUCTION_SYSTEM,
        user=TEMPLATE.format(title=title, key=key or "", context=ctx_text),
        schema=SectionInstruction,
        db=db,
    )

    # Harden required fields
    if not data.tone_rules:
        data.tone_rules = DEFAULT_TONE
    if not data.section_key:
        data.section_key = (key or title.lower().strip().replace(" ", "_")).replace("/", "_")
    if not data.title:
        data.title = title

    return data
