"""Pattern distillation from example proposal passages (project-aware).

Given a set of passages from example proposals for a specific section
(e.g., technical_approach), extract **reusable writing patterns** such as:
- common H2/H3 structure ordering
- types of proof (metrics, certifications, references)
- rhetorical moves (contrast, risk→mitigation, benefit-led phrasing)
- neutral phrase templates with variables (no client names)

This module deliberately tells the model **not to copy** sentences. The
result is a compact bullet list (<~250 tokens) used by the drafting
service to guide style/content without plagiarism.
"""
from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from .llm import chat_text_project

SYSTEM = (
    "You extract reusable writing patterns from proposal sections (structure, rhetorical moves, metric types). "
    "Do NOT copy sentences. Output concise bullet points under ~250 tokens."
)

PROMPT = """
You will summarize writing patterns for the `{section_key}` section of a government proposal.
Return concise bullet points that cover:
- Typical H2/H3 ordering
- Common proof types (metrics, certifications, tools)
- Rhetorical moves (contrast, benefit-led phrasing, risk→mitigation)
- Neutral phrase templates with variables (e.g., "We will <action> to achieve <metric> within <time>")
Do not include any real organization or person names.

Passages to analyze:
{passages}
"""


def extract_patterns(project_id: str, section_key: str, passages: List[str], db: Session) -> str:
    """Distill compact, reusable patterns from example passages.

    Falls back to section-typical guidance when no passages are provided.
    """
    # Keep the prompt small but representative
    cleaned = [p.strip() for p in passages[:6] if p and p.strip()]
    joined = "\n\n---\n\n".join(cleaned)

    if not joined:
        user = PROMPT.format(
            section_key=section_key,
            passages="(No passages available. Provide generic, section-typical patterns.)",
        )
    else:
        user = PROMPT.format(section_key=section_key, passages=joined)

    return chat_text_project(project_id, SYSTEM, user, db)
