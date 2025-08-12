# app/services/llm.py
"""Project-aware LLM helpers (wired to your root models.RfpProject)."""
import os
from functools import lru_cache
from typing import Type, Tuple

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError
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

def chat_json_project(project_id: str, system: str, user: str, schema: Type[BaseModel], db: Session):
    out = chat_text_project(project_id, system, user, db)
    try:
        return schema.model_validate_json(out)
    except ValidationError:
        # Handle code-fenced JSON returns like ```json ... ```
        cleaned = out.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return schema.model_validate_json(cleaned)
