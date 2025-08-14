# app/services/llm.py
"""Project-aware LLM helpers (wired to your root models.RfpProject)."""
import os
from functools import lru_cache
from typing import Type, Tuple

from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Defaults if a project has no explicit settings
DEFAULT_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2"))

# Your project model is in the root models.py
from models import RfpProject as ProjectModel  # <-- key change


@lru_cache(maxsize=64)
def _make_llm(model: str, temperature: float) -> ChatOpenAI:
    return ChatOpenAI(model=model, temperature=temperature)


def _resolve_project_settings(db: Session, project_id: str) -> Tuple[str, float]:
    """Return (model, temperature) for a project_id, or sensible defaults."""
    proj = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not proj:
        return DEFAULT_MODEL, DEFAULT_TEMPERATURE

    model = getattr(proj, "model_name", None) or DEFAULT_MODEL
    temp_val = getattr(proj, "temperature", None)
    try:
        temperature = float(temp_val) if temp_val is not None else DEFAULT_TEMPERATURE
    except Exception:
        temperature = DEFAULT_TEMPERATURE
    return model, temperature


def _llm_for_project(db: Session, project_id: str) -> ChatOpenAI:
    model, temperature = _resolve_project_settings(db, project_id)
    return _make_llm(model, temperature)


def chat_text_project(project_id: str, system: str, user: str, db: Session) -> str:
    llm = _llm_for_project(db, project_id)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return llm.invoke(msgs).content


def chat_html_project(project_id: str, system: str, user: str, db: Session) -> str:
    return chat_text_project(project_id, system, user, db)


def chat_json_project(
    project_id: str,
    system: str,
    user: str,
    schema: Type[BaseModel],
    db: Session,
):
    """
    Call the chat model and parse JSON output robustly, normalizing common LLM quirks:
      - code-fenced JSON (```json ... ```)
      - "length_hint_words" provided as a single int/str → coerce to {"min": ..., "max": ...}
      - list-like fields provided as a single string → split into list
      - backfill section_key from title if missing
    Then validate against the provided Pydantic schema.
    """
    raw = chat_text_project(project_id, system, user, db)

    # --- parse + normalize LLM JSON before validating ---
    import json, re

    # Strip common fencing
    cleaned = (raw or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json") :].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[: -3].strip()

    # Try direct JSON; else fallback to the first {...} block
    try:
        obj = json.loads(cleaned)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if not m:
            # Nothing JSON-like returned; surface the raw for debugging
            raise ValueError(f"LLM did not return valid JSON for schema parsing.\nRaw:\n{raw}")
        obj = json.loads(m.group(0))

    # If LLM returned a list at top-level, pick first dict if present
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        obj = obj[0]

    # Helper to coerce strings/lists into list[str]
    def _as_list(v):
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            # Prefer line-based splitting; fallback to semicolons; else single-item list
            lines = [s.strip(" -•\t").strip() for s in v.splitlines() if s.strip()]
            if len(lines) > 1:
                return lines
            parts = [s.strip() for s in v.split(";") if s.strip()]
            return parts or ([v.strip()] if v.strip() else [])
        return []

    if isinstance(obj, dict):
        # Coerce length_hint_words into {min,max}
        if "length_hint_words" in obj:
            lv = obj.get("length_hint_words")
            if isinstance(lv, (int, float, str)):
                try:
                    n = int(float(lv))
                except Exception:
                    n = 1500
                obj["length_hint_words"] = {
                    "min": max(300, int(n * 0.8)),
                    "max": max(int(n), int(n * 1.0)),
                }
            elif isinstance(lv, dict):
                # Fill missing min/max if only approx/min provided
                approx = lv.get("approx")
                try:
                    approx = int(float(approx)) if approx is not None else None
                except Exception:
                    approx = None
                mn = lv.get("min")
                mx = lv.get("max")
                try:
                    mn = int(float(mn)) if mn is not None else None
                except Exception:
                    mn = None
                try:
                    mx = int(float(mx)) if mx is not None else None
                except Exception:
                    mx = None
                if approx is not None:
                    mn = mn if mn is not None else max(300, int(approx * 0.8))
                    mx = mx if mx is not None else approx
                obj["length_hint_words"] = {
                    "min": mn if mn is not None else 1200,
                    "max": mx if mx is not None else max((mn or 1200) + 300, 1800),
                }
            else:
                obj["length_hint_words"] = {"min": 1200, "max": 1800}
        else:
            obj["length_hint_words"] = {"min": 1200, "max": 1800}

        # Coerce list-like fields when the model returns strings
        for k in [
            "must_include",
            "micro_outline",
            "tone_rules",
            "win_themes",
            "evidence_prompts",
            "compliance_checklist",
            "acceptance_criteria",
            "gaps",
        ]:
            if k in obj:
                obj[k] = _as_list(obj.get(k))

        # Backfill section_key from title if missing
        if not obj.get("section_key"):
            title = obj.get("title") or ""
            if isinstance(title, str) and title.strip():
                obj["section_key"] = (
                    title.lower().strip().replace(" ", "_").replace("/", "_")
                )

    # Finally, validate against the target schema
    try:
        return schema.model_validate(obj)
    except Exception:
        # last resort: dump then parse as json again
        import json as _json

        return schema.model_validate_json(_json.dumps(obj))
