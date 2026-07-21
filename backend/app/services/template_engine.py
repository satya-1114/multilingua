"""Template rendering engine.

Handles `{{var}}`, `{{var|default:...}}`, dot-nested paths, conditionals
`{% if var %}...{% endif %}`, localization via a language-code suffix on
templates, and validation with missing-variable detection.
"""
from __future__ import annotations

import re
from typing import Any

from app.core.exceptions import ValidationError


_VAR_PATTERN = re.compile(r"\{\{\s*([\w.]+)\s*(?:\|\s*default:\s*([^}]+?))?\s*\}\}")
_IF_PATTERN = re.compile(r"\{%\s*if\s+([\w.]+)\s*%\}(.*?)\{%\s*endif\s*%\}", re.DOTALL)
_FILTER_PATTERN = re.compile(r"\{\{\s*([\w.]+)\s*\|\s*(upper|lower|title|trim)\s*\}\}")


def _lookup(source: dict[str, Any], path: str) -> Any:
    cur: Any = source
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    if isinstance(value, (int, float)):
        return bool(value)
    return True


def render(body: str, variables: dict[str, Any], *, strict: bool = False) -> tuple[str, list[str]]:
    """Render `body`.

    Returns (rendered_text, missing_variables). When ``strict`` is true,
    missing variables raise :class:`ValidationError`.
    """
    missing: list[str] = []

    # Conditionals first.
    def _if_sub(match: re.Match[str]) -> str:
        path, inner = match.group(1), match.group(2)
        return inner if _truthy(_lookup(variables, path)) else ""
    processed = _IF_PATTERN.sub(_if_sub, body)

    # Filters (upper/lower/title/trim) — resolved before generic variables.
    def _filter_sub(match: re.Match[str]) -> str:
        path, filt = match.group(1), match.group(2)
        value = _lookup(variables, path)
        if value is None:
            missing.append(path)
            return ""
        text = str(value)
        return {"upper": text.upper(), "lower": text.lower(), "title": text.title(), "trim": text.strip()}[filt]
    processed = _FILTER_PATTERN.sub(_filter_sub, processed)

    def _var_sub(match: re.Match[str]) -> str:
        path = match.group(1)
        default = (match.group(2) or "").strip()
        value = _lookup(variables, path)
        if value is None or value == "":
            if default:
                return default
            missing.append(path)
            return "" if not strict else ""
        return str(value)

    rendered = _VAR_PATTERN.sub(_var_sub, processed)

    if strict and missing:
        raise ValidationError(
            "Template is missing required variables",
            details={"missing": sorted(set(missing))},
        )
    return rendered, sorted(set(missing))


def variables_in(body: str) -> list[str]:
    """Extract every variable path referenced in `body`."""
    found = set()
    for match in _VAR_PATTERN.finditer(body):
        found.add(match.group(1))
    for match in _FILTER_PATTERN.finditer(body):
        found.add(match.group(1))
    for match in _IF_PATTERN.finditer(body):
        found.add(match.group(1))
    return sorted(found)


def validate(body: str, provided_variables: dict[str, Any] | None = None) -> dict[str, Any]:
    provided = provided_variables or {}
    referenced = variables_in(body)
    missing = [v for v in referenced if _lookup(provided, v) in (None, "")]
    return {"variables": referenced, "missing": missing, "valid": not missing}


def preview(body: str, variables: dict[str, Any]) -> str:
    rendered, _ = render(body, variables)
    return rendered
