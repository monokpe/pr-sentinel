"""
PR Sentinel — data models.
All data flowing between agents is typed here.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ---------------------------------------------------------------------------
# Diff / repo context
# ---------------------------------------------------------------------------

class FileDiff(BaseModel):
    path: str
    old_path: str | None = None          # set when file was renamed
    additions: int = 0
    deletions: int = 0
    patch: str = ""                       # raw unified diff text


class RepoContext(BaseModel):
    """Everything the orchestrator knows about the change being reviewed."""
    repo_path: str
    base_branch: str = "main"
    head_branch: str = ""
    pr_title: str = ""
    pr_description: str = ""
    files_changed: list[FileDiff] = Field(default_factory=list)
    # key = file path, value = full current source (populated on demand)
    full_file_contents: dict[str, str] = Field(default_factory=dict)
    # mutable bag for inter-agent communication (e.g. PlanAgent → specialists)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Individual findings
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    agent: str                            # which subagent produced this
    severity: Severity
    file: str = ""
    line: int | None = None
    title: str
    detail: str
    suggestion: str = ""


# ---------------------------------------------------------------------------
# Per-agent results
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    agent: str
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
    raw_response: str = ""               # full LLM output for debugging
    error: str | None = None             # set if the agent failed


# ---------------------------------------------------------------------------
# Final merged report
# ---------------------------------------------------------------------------

class ReviewReport(BaseModel):
    repo_path: str
    pr_title: str
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    agent_results: list[AgentResult] = Field(default_factory=list)
    human_review: str = ""               # prose from ReviewDrafterAgent
    metadata: dict[str, Any] = Field(default_factory=dict)
