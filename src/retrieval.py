"""
retrieval.py
Simple RAG-style retrieval: given a clause's category, look up the relevant
reference norms from data/reference_norms.json. This grounds the risk scoring
and explanations in a defined knowledge base rather than free-form LLM guessing.

For a larger dataset, swap the JSON lookup for a FAISS/Chroma vector search
over embedded reference documents -- the interface (get_reference) stays the same.
"""
import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reference_norms.json")

_cache = None


def _load_norms(path: str = _DEFAULT_PATH) -> dict:
    global _cache
    if _cache is None:
        with open(path, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def get_reference(category: str, path: str = _DEFAULT_PATH) -> dict:
    """Return the reference norm entry for a given clause category, or {} if none exists."""
    norms = _load_norms(path)
    return norms.get(category, {})
