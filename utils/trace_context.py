"""Trace metadata shared by every graph.

LangSmith Engine uses the ``revision_id`` metadata key to link each trace to
the commit that produced it, so it can compare releases when a metric
regresses. The ``agent`` key lets Engine and Insights scope analysis to a
single workflow inside the shared tracing project.

This module has no import-time side effects so it is safe to import from
graphs loaded by ``langgraph dev``.
"""

import os
import subprocess
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=1)
def get_revision_id() -> Optional[str]:
    """Return the deployed revision (REVISION_ID env var, else the git short SHA)."""
    revision = os.getenv("REVISION_ID")
    if revision:
        return revision

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def get_trace_context(agent_name: str) -> dict:
    """Get metadata to attach to every trace for a given agent."""
    metadata = {"agent": agent_name}

    revision_id = get_revision_id()
    if revision_id:
        metadata["revision_id"] = revision_id

    return metadata
