"""Centralized retrieval helpers for project RFP/KB context and example passages."""
from __future__ import annotations

from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session

from chromadb import PersistentClient
from app.core.config import DB_DIRECTORY, EXAMPLES_COLLECTION
import crud

# Single persistent Chroma client
_client = PersistentClient(path=DB_DIRECTORY)


def _get_or_create(name: str):
    try:
        return _client.get_collection(name)
    except Exception:
        return _client.create_collection(name)


def _dedupe(docs: List[str], metas: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """De-duplicate by (doc, source, page) while preserving order."""
    seen = set()
    out_docs: List[str] = []
    out_meta: List[Dict[str, Any]] = []
    for d, m in zip(docs, metas):
        key = (d, (m or {}).get("source"), (m or {}).get("page"))
        if key in seen:
            continue
        seen.add(key)
        out_docs.append(d)
        out_meta.append(m)
    return out_docs, out_meta


def _k_from_project(db: Optional[Session], project_id: str, default: int = 12) -> int:
    """Map project.context_size → K."""
    if not db:
        return default
    try:
        proj = crud.get_project_by_project_id(db, project_id)
        size = getattr(proj, "context_size", None) or "medium"
        mapping = {"low": 8, "medium": 12, "high": 18}
        return mapping.get(size, default)
    except Exception:
        return default


def retrieve_project_context(
    project_id: str,
    use_kb: bool = False,
    db: Optional[Session] = None,
    query_text: str = "proposal context",
    k: Optional[int] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Get top-K snippets from the project's collection (and optional KB).

    Returns: (snippets, meta) where meta entries include `id` and `kind` of "RFP" or "KB".
    """
    nk = k or _k_from_project(db, project_id, 12)

    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    # Project (RFP) collection
    try:
        coll = _get_or_create(project_id)
        q = coll.query(query_texts=[query_text], n_results=nk, include=["documents", "metadatas", "ids"])
        cd = q.get("documents", [[]])[0]
        cm = q.get("metadatas", [[]])[0]
        ci = q.get("ids", [[]])[0]
        for m, i in zip(cm, ci):
            m = dict(m or {})
            m["id"] = i
            m["kind"] = "RFP"
            metas.append(m)
        docs.extend(cd)
    except Exception:
        pass

    # Knowledge base
    if use_kb:
        try:
            kb = _get_or_create("knowledge_base")
            q = kb.query(query_texts=[query_text], n_results=max(4, nk // 3), include=["documents", "metadatas", "ids"])
            kd = q.get("documents", [[]])[0]
            km = q.get("metadatas", [[]])[0]
            ki = q.get("ids", [[]])[0]
            for m, i in zip(km, ki):
                m = dict(m or {})
                m["id"] = i
                m["kind"] = "KB"
                metas.append(m)
            docs.extend(kd)
        except Exception:
            pass

    docs, metas = _dedupe(docs, metas)
    return docs, metas


def retrieve_example_passages(
    section_key: str,
    example_ids: Optional[List[str]] = None,
    filters: Optional[Dict[str, str]] = None,
    k: int = 8,
    query_text: str = "patterns for section",
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Get example passages for a section_key from the `EXAMPLES_COLLECTION`."""
    col = _get_or_create(EXAMPLES_COLLECTION)
    where: Dict[str, Any] = {"section_key": section_key}
    if filters:
        where.update({kk: vv for kk, vv in filters.items() if vv})

    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    try:
        if example_ids:
            where_in = dict(where)
            where_in["example_id"] = {"$in": example_ids}
            q = col.query(query_texts=[query_text], where=where_in, n_results=k, include=["documents", "metadatas", "ids"])
        else:
            q = col.query(query_texts=[query_text], where=where, n_results=k, include=["documents", "metadatas", "ids"])

        dd = q.get("documents", [[]])[0]
        mm = q.get("metadatas", [[]])[0]
        ii = q.get("ids", [[]])[0]
        for m, i in zip(mm, ii):
            m = dict(m or {})
            m["id"] = i
            m["kind"] = "EX"
            metas.append(m)
        docs.extend(dd)
    except Exception:
        # fallback: over-fetch + client-side filter (covers servers without $in support)
        try:
            q = col.query(query_texts=[query_text], n_results=max(50, k * 4), include=["documents", "metadatas", "ids"])
            dd = q.get("documents", [[]])[0]
            mm = q.get("metadatas", [[]])[0]
            ii = q.get("ids", [[]])[0]
            ex_id_set = set(example_ids or [])
            for d, m, i in zip(dd, mm, ii):
                if m and m.get("section_key") != section_key:
                    continue
                if filters and any((filters.get(f) and m.get(f) != filters.get(f)) for f in filters):
                    continue
                if example_ids and (m.get("example_id") not in ex_id_set):
                    continue
                m = dict(m or {})
                m["id"] = i
                m["kind"] = "EX"
                docs.append(d)
                metas.append(m)
            # trim
            docs = docs[:k]
            metas = metas[:k]
        except Exception:
            pass

    docs, metas = _dedupe(docs, metas)
    return docs, metas
