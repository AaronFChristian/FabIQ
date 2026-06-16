"""
FabIQ Prompt Registry.

All prompts are stored in prompts.json, versioned, and loaded here.
Changing a prompt means adding a new version entry in the JSON — never
editing an existing one. This makes every prompt change:
  - Auditable  (version history in the JSON)
  - Testable   (run eval suite against new version before promoting)
  - Reversible (roll back by changing active_version in the JSON)

Usage:
    from fabiq.pipeline.prompt_registry import get_prompt

    system_prompt = get_prompt("agent_4_citation_grounding")
    temperature   = get_prompt("agent_4_citation_grounding", field="temperature")
    version       = get_prompt("agent_4_citation_grounding", field="version")
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROMPTS_PATH = Path(__file__).parent / "prompts.json"


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Any]:
    """Load and cache the prompts registry from disk."""
    with _PROMPTS_PATH.open() as f:
        return json.load(f)


def get_active_version() -> str:
    """Return the currently active prompt version string."""
    return _load_registry()["active_version"]


def get_prompt(
    agent_key: str,
    *,
    version: str | None = None,
    field: str = "system",
) -> Any:
    """
    Retrieve a prompt field for a given agent and version.

    Args:
        agent_key: Key in the prompts registry, e.g. "agent_4_citation_grounding"
        version:   Specific version to load, e.g. "v1.1". Defaults to active_version.
        field:     Field to return: "system", "temperature", "max_tokens", "notes", "version"

    Returns:
        The requested field value, or the version string if field="version".

    Raises:
        KeyError: If agent_key or version not found in registry.
    """
    registry = _load_registry()
    resolved_version = version or registry["active_version"]

    if field == "version":
        return resolved_version

    prompts = registry["prompts"]
    if agent_key not in prompts:
        raise KeyError(f"Agent key {agent_key!r} not found in prompt registry")

    agent_versions = prompts[agent_key]
    if resolved_version not in agent_versions:
        # Fall back to latest available version for this agent
        latest = sorted(agent_versions.keys())[-1]
        resolved_version = latest

    return agent_versions[resolved_version].get(field)


def get_changelog() -> list[dict[str, str]]:
    """Return the full version changelog for display in the dashboard."""
    return _load_registry()["_meta"]["changelog"]


def list_versions(agent_key: str) -> list[str]:
    """Return all available version strings for an agent."""
    registry = _load_registry()
    return sorted(registry["prompts"].get(agent_key, {}).keys())


def invalidate_cache() -> None:
    """Force reload of the registry from disk (call after updating prompts.json)."""
    _load_registry.cache_clear()
