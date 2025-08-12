from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services.examples import ingest_example_file
from app.models.examples import ProposalExample, ExampleSection

router = APIRouter(prefix="/examples", tags=["examples"])


@router.post("/upload")
async def upload_examples(
    files: List[UploadFile] = File(...),
    title: Optional[str] = Form(None),
    client_type: Optional[str] = Form(None),
    domain: Optional[str] = Form(None),
    contract_vehicle: Optional[str] = Form(None),
    complexity_tier: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload one or more proposal example files.

    Stores files under EXAMPLES_DIRECTORY, extracts text, slices into sections,
    and indexes chunks into the Chroma `examples` collection.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    created_ids: List[str] = []
    for f in files:
        tmp_path = f"/tmp/{f.filename}"
        # Save to a temporary file first
        contents = await f.read()
        with open(tmp_path, "wb") as out:
            out.write(contents)

        meta = {
            "title": title or f.filename,
            "client_type": client_type,
            "domain": domain,
            "contract_vehicle": contract_vehicle,
            "complexity_tier": complexity_tier,
        }
        ex_id = ingest_example_file(db, tmp_path, meta)
        created_ids.append(ex_id)

    return {"example_ids": created_ids}


@router.get("")
def list_examples(db: Session = Depends(get_db)):
    """Return metadata for all uploaded examples (lightweight)."""
    rows = db.query(ProposalExample).order_by(ProposalExample.created_at.desc().nullslast()).all()
    items = []
    for r in rows:
        # naive section count; fine for small libraries
        sections_count = db.query(ExampleSection).filter(ExampleSection.example_id == r.id).count()
        items.append({
            "id": str(r.id),
            "title": r.title,
            "client_type": r.client_type,
            "domain": r.domain,
            "contract_vehicle": r.contract_vehicle,
            "complexity_tier": r.complexity_tier,
            "ingest_status": r.ingest_status,
            "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
            "sections_count": sections_count,
        })
    return {"examples": items}


@router.get("/{example_id}/sections")
def get_example_sections(example_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """Return section texts for a given example (truncated previews)."""
    ex = db.query(ProposalExample).filter(ProposalExample.id == example_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Example not found")

    q = (
        db.query(ExampleSection)
        .filter(ExampleSection.example_id == example_id)
        .order_by(ExampleSection.section_key.asc())
    )
    sections = q.limit(max(1, min(limit, 100))).all()

    def _preview(txt: str, n: int = 400) -> str:
        t = (txt or "").strip()
        return t[:n] + ("…" if len(t) > n else "")

    return {
        "example_id": example_id,
        "sections": [
            {
                "section_key": s.section_key,
                "preview": _preview(s.text),
                "tokens": s.tokens,
                "quality_score": s.quality_score,
            }
            for s in sections
        ],
    }
