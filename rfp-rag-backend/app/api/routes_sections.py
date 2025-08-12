from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.sections import (
    GenerateInstructionsReq,
    SectionInstruction,
    DraftReq,
    DraftResp,
)
from app.models.examples import SectionInstructionRow
from app.services.instructions import build_instruction
from app.services.drafting import draft_section as _draft
from app.services.retrieval import retrieve_project_context

router = APIRouter(prefix="/rfps", tags=["sections"])


@router.post("/{project_id}/sections/instructions")
def generate_instructions(
    project_id: str,
    body: GenerateInstructionsReq,
    db: Session = Depends(get_db),
):
    """Generate structured Instruction Sheets for each outline item.

    - Retrieves a few relevant RFP/KB snippets to tailor the guidance
    - Calls the project-aware LLM to produce a SectionInstruction JSON for each section
    - Persists the resulting JSON rows in `section_instructions` for history/auditing
    """
    if not body.outline:
        raise HTTPException(status_code=400, detail="Outline is empty")

    # Pull context once (lightweight); each instruction is short and schema-validated
    ctx_snips, _ = retrieve_project_context(project_id, use_kb=body.use_knowledge_base)

    out: List[SectionInstruction] = []
    for item in body.outline:
        instr = build_instruction(project_id, item.title, item.key, ctx_snips, db)
        out.append(instr)
        db.add(
            SectionInstructionRow(
                project_id=project_id,
                section_key=instr.section_key,
                json=instr.model_dump(),
            )
        )

    db.commit()
    return {"instructions": [i.model_dump() for i in out]}


@router.post("/{project_id}/sections/{section_key}/draft", response_model=DraftResp)
async def draft_section_endpoint(
    project_id: str,
    section_key: str,
    body: DraftReq,
    db: Session = Depends(get_db),
) -> DraftResp:
    """Draft a proposal section using:
    - the provided Instruction JSON,
    - optional example IDs/filters for pattern extraction,
    - and RFP/KB snippets from the project's vector stores.
    Returns HTML plus similarity & compliance checks.
    """
    # Optional guard: ensure instruction key matches path
    if body.instruction and body.instruction.section_key and body.instruction.section_key != section_key:
        raise HTTPException(status_code=400, detail="instruction.section_key does not match URL section_key")

    return _draft(
        project_id,
        body.instruction,
        body.use_knowledge_base,
        body.example_ids,
        body.filters,
        db=db,
    )
