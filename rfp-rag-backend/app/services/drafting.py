"""Section drafting service (project-aware).

Combines:
- Instruction JSON (what to write, tone, compliance checklist)
- Example-derived patterns (how to write—structure/rhetoric/templates)
- Retrieved context from the project's RFP collection (and optional KB)

Returns HTML plus basic quality checks (similarity vs examples, checklist coverage).
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from .retrieval import retrieve_project_context, retrieve_example_passages
from .patterns import extract_patterns
from .llm import chat_html_project
from .similarity import max_sentence_similarity
from .compliance import check_compliance
from app.schemas.sections import SectionInstruction, DraftResp

# System guidance for drafting
SYSTEM = (
    "You are a capture manager and principal proposal writer. "
    "Follow the instruction JSON exactly, be compliant, specific, and evidence-driven. "
    "Use headings (H2/H3). Do not include pricing. If relying on a snippet, reference it as [S1], [S2], ..."
)

# User prompt template
PROMPT = """
Instruction JSON:
{instruction_json}

Patterns distilled from prior winning examples — do not copy text:
{patterns}

RFP/KB context snippets:
{context}

Write the full section now.
"""


def draft_section(
    project_id: str,
    instruction: SectionInstruction,
    use_kb: bool,
    example_ids: Optional[list[str]] = None,
    filters: Optional[dict] = None,
    db: Session | None = None,
) -> DraftResp:
    """Draft a section and run post-generation checks.

    Args:
        project_id: public string ID for the project's vector collection.
        instruction: validated SectionInstruction to follow.
        use_kb: whether to include knowledge_base retrieval.
        example_ids: optional list of specific example UUIDs to bias patterns.
        filters: optional metadata filters {client_type, domain, contract_vehicle, complexity_tier}.
        db: SQLAlchemy session to resolve per-project LLM settings.
    """
    # 1) Retrieve context
    query_hint = f"{instruction.title} — " + "; ".join(instruction.micro_outline[:4]) if instruction.micro_outline else instruction.title
    ctx_snips, ctx_meta = retrieve_project_context(
        project_id, use_kb=use_kb, db=db, query_text=query_hint
    )

    # 2) Pull example passages & distill patterns (no copying)
    ex_passages, ex_meta = retrieve_example_passages(
        instruction.section_key, example_ids, filters, k=8, query_text=f"{instruction.section_key} patterns"
    )
    patterns = extract_patterns(project_id, instruction.section_key, ex_passages, db)

    # 3) Draft
    html = chat_html_project(
        project_id,
        SYSTEM,
        PROMPT.format(
            instruction_json=instruction.model_dump_json(),
            patterns=patterns,
            context="\n\n".join(ctx_snips[:10]),
        ),
        db=db,
    )

    # 4) Checks: similarity vs examples (to avoid copying) + checklist coverage
    sim = max_sentence_similarity(html, ex_passages)
    comp = check_compliance(html, instruction.compliance_checklist)

    # 5) Provenance
    sources = [
        {"id": m.get("id", ""), "kind": m.get("kind", "RFP"), "meta": m}
        for m in (ctx_meta + ex_meta)
    ]

    return DraftResp(html=html, sources=sources, checks={"similarity": sim, "compliance": comp})
