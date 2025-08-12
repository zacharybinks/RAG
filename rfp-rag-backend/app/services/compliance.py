"""Lightweight compliance checker for drafted sections.

Purpose
-------
Given a generated section (HTML) and a checklist of compliance items, 
return a simple pass/fail signal per item using keyword presence.

Notes
-----
- This is intentionally minimal and fast. It strips HTML to text and
  checks whether the key terms from each checklist line appear in the draft.
- It is *not* a legal/comprehensive compliance audit. It's a guard-rail
  that surfaces likely gaps for a human to verify.
- You can later extend this with an LLM justification step (e.g., explain
  where/how the requirement is addressed) without changing the return shape.
"""
from __future__ import annotations

from typing import List, Dict
import re
from bs4 import BeautifulSoup


def _to_text(html: str) -> str:
    """Strip HTML and normalize to lowercase plain text."""
    return BeautifulSoup(html or "", "html.parser").get_text(" ").lower()


def _tokens(line: str) -> List[str]:
    """Crude tokenizer for a checklist item (letters/numbers only)."""
    return re.findall(r"[a-zA-Z0-9]+", (line or "").lower())


def check_compliance(html: str, checklist: List[str]) -> List[Dict[str, object]]:
    """Return a list of {item, met, method} dicts.

    Heuristic: take up to the first 6 non-trivial tokens from each item
    (>=3 chars) and require that all are present in the draft text.
    """
    text = _to_text(html)
    out: List[Dict[str, object]] = []

    for item in checklist or []:
        toks = [t for t in _tokens(item) if len(t) >= 3][:6]
        met = bool(toks) and all(t in text for t in toks)
        out.append({"item": item, "met": met, "method": "keyword"})

    return out
