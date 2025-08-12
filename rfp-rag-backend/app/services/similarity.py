"""Draft-vs-examples similarity check.

Purpose
-------
Compute the maximum sentence-level cosine similarity between the generated
HTML draft and the example passages used to guide style. This helps flag
accidental copying while still allowing pattern reuse.

Implementation details
----------------------
- Strips HTML -> plain text, then tokenizes into naive sentences (split on ".").
- Embeds sentences with `sentence-transformers` (MiniLM) and computes
  cosine similarity between all pairs (draft x examples).
- Returns `{ "max": float, "flag": bool }` where `flag` is true if
  `max >= threshold` (default 0.92).

Notes
-----
- The model is loaded lazily to avoid import-time overhead.
- Threshold 0.92 is conservative; adjust per your QA policy.
"""
from __future__ import annotations

from typing import List, Dict

from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util

# Lazy global model (loads on first use)
_model = None  # type: SentenceTransformer | None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _sentences_from_html(html: str) -> List[str]:
    """Very simple sentence splitter suitable for similarity checks."""
    txt = BeautifulSoup(html or "", "html.parser").get_text(" ")
    # naive split on period — good enough for a plagiarism guard
    sents = [s.strip() for s in txt.split(".") if s and s.strip()]
    return sents


def max_sentence_similarity(html: str, example_passages: List[str], threshold: float = 0.92) -> Dict[str, object]:
    """Return a dict with the maximum sentence similarity and a boolean flag.

    Args:
        html: generated section HTML to evaluate.
        example_passages: raw text passages from example sections.
        threshold: cosine similarity threshold to flag potential copying.
    """
    draft_sents = _sentences_from_html(html)

    ex_sents: List[str] = []
    for p in example_passages or []:
        ex_sents.extend([s.strip() for s in (p or "").split(".") if s and s.strip()])

    if not draft_sents or not ex_sents:
        return {"max": 0.0, "flag": False}

    model = _get_model()
    emb_d = model.encode(draft_sents, convert_to_tensor=True, normalize_embeddings=True)
    emb_e = model.encode(ex_sents, convert_to_tensor=True, normalize_embeddings=True)

    sim = util.cos_sim(emb_d, emb_e).cpu().numpy()
    max_val = float(sim.max()) if sim.size else 0.0

    return {"max": max_val, "flag": max_val >= threshold}
