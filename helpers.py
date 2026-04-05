"""
Shared utility functions for the Business Co-Founder AI system.
"""
import json
import re
from typing import Any


def extract_json_from_llm(text: str) -> dict | list | None:
    """
    Robustly extracts JSON from LLM output that may contain markdown fences,
    explanation text, or other noise around the JSON.
    """
    if not text:
        return None
    
    # Try 1: Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try 2: Extract from ```json ... ``` blocks
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Try 3: Find first { ... } or [ ... ] block
    brace_match = re.search(r'(\{.*\})', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass
    
    bracket_match = re.search(r'(\[.*\])', text, re.DOTALL)
    if bracket_match:
        try:
            return json.loads(bracket_match.group(1))
        except json.JSONDecodeError:
            pass
    
    return None


def clamp(value: float, min_val: float = 1.0, max_val: float = 10.0) -> float:
    """Clamp a numeric value to a range."""
    return max(min_val, min(max_val, value))


def safe_get(data: dict, *keys, default: Any = "") -> Any:
    """Safely traverse nested dicts."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def truncate(text: str, max_len: int = 500) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def build_numbered_context(sources: list[dict]) -> str:
    """Build a numbered research context string from source metadata."""
    context = ""
    for s in sources:
        num = s.get("number", "?")
        title = s.get("title", "Unknown")
        body = s.get("body", s.get("snippet", ""))
        context += f"\n--- SOURCE [{num}] ---\nTITLE: {title}\nCONTENT: {body}\n"
    return context
