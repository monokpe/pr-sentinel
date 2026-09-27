"""
Unit tests for pr_sentinel.models
"""
import pytest
from pr_sentinel.models import (
    Severity, FileDiff, RepoContext, Finding, AgentResult, ReviewReport
)


def test_severity_enum_values():
    assert Severity.CRITICAL.value == "critical"
    assert Severity.HIGH.value == "high"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.LOW.value == "low"
    assert Severity.INFO.value == "info"


def test_file_diff_defaults():
    fd = FileDiff(path="foo.py")
    assert fd.additions == 0
    assert fd.deletions == 0
    assert fd.patch == ""
    assert fd.old_path is None


def test_repo_context_defaults():
    ctx = RepoContext(repo_path="/tmp/repo")
    assert ctx.base_branch == "main"
    assert ctx.head_branch == ""
    assert ctx.files_changed == []
    assert ctx.full_file_contents == {}
    assert ctx.metadata == {}


def test_repo_context_metadata_mutable():
    ctx = RepoContext(repo_path="/tmp/repo")
    ctx.metadata["plan_review_focus"] = "check auth"
    assert ctx.metadata["plan_review_focus"] == "check auth"


def test_finding_construction():
    f = Finding(
        agent="SecurityAgent",
        severity=Severity.CRITICAL,
        file="api.py",
        line=42,
        title="Hardcoded key",
        detail="Key is plaintext",
        suggestion="Use env var",
    )
    assert f.agent == "SecurityAgent"
    assert f.severity == Severity.CRITICAL
    assert f.line == 42


def test_agent_result_defaults():
    r = AgentResult(agent="TestAgent")
    assert r.findings == []
    assert r.summary == ""
    assert r.error is None


def test_review_report_defaults():
    rr = ReviewReport(repo_path="/tmp", pr_title="My PR")
    assert rr.total_findings == 0
    assert rr.critical_count == 0
    assert rr.human_review == ""
    assert rr.agent_results == []
