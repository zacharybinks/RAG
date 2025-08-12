"""Upload + ingest service for proposal examples.

Responsibilities
- Save uploaded files into EXAMPLES_DIRECTORY
- Extract text (PDF or DOCX; fallback to plain text)
- Slice into rough sections and persist to SQL (proposal_examples, example_sections)
- Upsert section texts into the Chroma `EXAMPLES_COLLECTION` with useful metadata

Notes
- Section splitting is intentionally simple (regex on common headings) but
  can be upgraded later (LLM-aided classifier) without changing call sites.
- We index section-level texts so retrieval for a given `section_key` is clean.
"""
from __future__ import annotations

import os
import re
from typing import List, Tuple
from uuid import uuid4

from chromadb import PersistentClient
from sqlalchemy.orm import Session

from app.core.config import DB_DIRECTORY, EXAMPLES_DIRECTORY, EXAMPLES_COLLECTION
from app.models.examples import ProposalExample, ExampleSection

# Lightweight extractors
from pypdf import PdfReader
import docx

# Single persistent Chroma client
_client = PersistentClient(path=DB_DIRECTORY)


def _ensure_examples_collection():
    try:
        return _client.get_collection(EXAMPLES_COLLECTION)
    except Exception:
        return _client.create_collection(EXAMPLES_COLLECTION)


# ---------------------------
# Text extraction
# ---------------------------

def _extract_text_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join([p.extract_text() or "" for p in reader.pages])


def _extract_text_docx(path: str) -> str:
    d = docx.Document(path)
    return "\n".join([p.text for p in d.paragraphs])


# ---------------------------
# Section slicing
# ---------------------------

# Map common proposal headings to canonical keys (extensible)
_CANONICAL = {
    "EXECUTIVE SUMMARY": "exec_summary",
    "TECHNICAL APPROACH": "technical_approach",
    "MANAGEMENT": "management_approach",
    "MANAGEMENT APPROACH": "management_approach",
    "STAFFING": "staffing",
    "KEY PERSONNEL": "staffing",
    "TRANSITION": "transition",
    "PHASE-IN": "transition",
    "QUALITY": "qa_qc",
    "QUALITY ASSURANCE": "qa_qc",
    "QUALITY CONTROL": "qa_qc",
    "RISK": "risk",
    "RISK MANAGEMENT": "risk",
    "PAST PERFORMANCE": "past_performance",
    "COMPLIANCE": "compliance_matrix",
    "PRICING": "pricing_narrative",
}

# Regex capturing headings on their own line; add more tokens as needed
_HEADING_RE = re.compile(
    r"\n\s*(EXECUTIVE SUMMARY|TECHNICAL APPROACH|MANAGEMENT(?: APPROACH)?|STAFFING|KEY PERSONNEL|TRANSITION|PHASE-IN|QUALITY(?: ASSURANCE| CONTROL)?|RISK(?: MANAGEMENT)?|PAST PERFORMANCE|COMPLIANCE|PRICING)\s*\n",
    flags=re.IGNORECASE,
)


def _canonical_key(title: str) -> str:
    upper = title.upper().strip()
    key = _CANONICAL.get(upper)
    if key:
        return key
    # generic fallback
    return upper.lower().replace(" ", "_")


def _split_sections(text: str) -> List[Tuple[str, str]]:
    """Return a list of (section_key, body_text) tuples.

    If no headings are found, the entire document is returned as one section.
    """
    parts = _HEADING_RE.split(text)
    if len(parts) <= 1:
        return [("full_document", text)]

    # parts = [pre, H1, body1, H2, body2, ...]
    sections: List[Tuple[str, str]] = []
    for i in range(1, len(parts), 2):
        title = (parts[i] or "").strip()
        body = (parts[i + 1] if i + 1 < len(parts) else "").strip()
        key = _canonical_key(title)
        if body:
            sections.append((key, body))
    return sections or [("full_document", text)]


# ---------------------------
# Ingest pipeline
# ---------------------------

def ingest_example_file(db: Session, file_path: str, meta: dict) -> str:
    """Persist an uploaded example and index its sections into Chroma.

    Args:
        db: SQLAlchemy session
        file_path: temporary path of the uploaded file
        meta: dict with optional keys (title, client_type, domain, contract_vehicle, complexity_tier, tags)

    Returns:
        The new example's UUID string.
    """
    os.makedirs(EXAMPLES_DIRECTORY, exist_ok=True)
    filename = os.path.basename(file_path)
    target = os.path.join(EXAMPLES_DIRECTORY, filename)

    # Move file into examples directory
    if file_path != target:
        try:
            os.replace(file_path, target)
        except Exception:
            # Fallback: copy then remove
            with open(file_path, "rb") as src, open(target, "wb") as dst:
                dst.write(src.read())
            try:
                os.remove(file_path)
            except Exception:
                pass

    # Create DB row for the example
    ex = ProposalExample(
        title=meta.get("title") or filename,
        source_path=target,
        client_type=meta.get("client_type"),
        domain=meta.get("domain"),
        contract_vehicle=meta.get("contract_vehicle"),
        complexity_tier=meta.get("complexity_tier"),
        tags=meta.get("tags"),
        ingest_status="queued",
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)

    # Extract text per file type
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = _extract_text_pdf(target)
    elif lower.endswith(".docx"):
        text = _extract_text_docx(target)
    else:
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    # Split and persist sections
    sections = _split_sections(text)
    col = _ensure_examples_collection()

    ids: List[str] = []
    docs: List[str] = []
    metas: List[dict] = []

    for section_key, body in sections:
        row = ExampleSection(example_id=ex.id, section_key=section_key, text=body)
        db.add(row)
        # Prepare Chroma payloads
        ids.append(str(uuid4()))
        docs.append(body)
        metas.append(
            {
                "example_id": str(ex.id),
                "section_key": section_key,
                "client_type": ex.client_type,
                "domain": ex.domain,
                "contract_vehicle": ex.contract_vehicle,
                "complexity_tier": ex.complexity_tier,
            }
        )

    db.commit()

    # Vectorize section bodies
    if docs:
        try:
            col.add(ids=ids, documents=docs, metadatas=metas)
        except Exception:
            # If Chroma throws on malformed docs, skip indexing but keep DB rows
            pass

    ex.ingest_status = "done"
    db.add(ex)
    db.commit()

    return str(ex.id)
