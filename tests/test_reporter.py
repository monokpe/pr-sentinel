"""
Unit tests for pr_sentinel.reporter
"""
import json
from pr_sentinel.models import (
    AgentResult, Finding, ReviewReport, Severity
)
from pr_sentinel import reporter


def _make_report(**kwargs) -> ReviewReport:
    defaults = dict(
        repo_path="/tmp/repo",
        pr_title="Test PR",
        total_findings=0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        agent_results=[],
        human_review="",
    )
    defaults.update(kwargs)
    return ReviewReport(**defaults)


def test_markdown_contains_header():
    rpt = _make_report()
    md = reporter.to_markdown(rpt)
    assert "# PR Sentinel Report" in md
    assert "Test PR" in md


def test_markdown_summary_table():
    rpt = _make_report(critical_count=2, high_count=1, total_findings=3)
    md = reporter.to_markdown(rpt)
    assert "| 🔴 Critical | 2 |" in md
    assert "| 🟠 High     | 1 |" in md
    assert "| **Total**  | **3** |" in md


def test_markdown_includes_human_review():
    rpt = _make_report(human_review="## PR Review\n\n**Verdict:** Approve")
    md = reporter.to_markdown(rpt)
    assert "**Verdict:** Approve" in md


def test_markdown_skips_review_drafter_in_structured_section():
    drafter = AgentResult(agent="ReviewDrafterAgent", raw_response="prose here")
    rpt = _make_report(agent_results=[drafter], human_review="prose here")
    md = reporter.to_markdown(rpt)
    # ReviewDrafterAgent should not appear in the structured findings section
    # (it's already shown as human_review)
    assert "### ReviewDrafterAgent" not in md


def test_markdown_renders_plan_agent():
    plan_data = {
        "pr_summary": "Adds OAuth support",
        "areas_touched": ["auth.py"],
        "red_flags": ["Touches auth layer"],
        "review_focus": "Check token handling",
    }
    plan = AgentResult(
        agent="PlanAgent",
        summary="plan summary",
        raw_response=json.dumps(plan_data),
    )
    rpt = _make_report(agent_results=[plan])
    md = reporter.to_markdown(rpt)
    assert "Adds OAuth support" in md
    assert "Touches auth layer" in md
    assert "Check token handling" in md


def test_markdown_renders_findings():
    finding = Finding(
        agent="SecurityAgent",
        severity=Severity.CRITICAL,
        file="api.py",
        line=10,
        title="Hardcoded key",
        detail="Key is plaintext",
        suggestion="Use env var",
    )
    sec = AgentResult(agent="SecurityAgent", findings=[finding], summary="1 critical")
    rpt = _make_report(agent_results=[sec], total_findings=1, critical_count=1)
    md = reporter.to_markdown(rpt)
    assert "Hardcoded key" in md
    assert "api.py:10" in md
    assert "Use env var" in md


def test_json_output_is_valid():
    rpt = _make_report(total_findings=0)
    raw = reporter.to_json(rpt)
    data = json.loads(raw)
    assert data["pr_title"] == "Test PR"
    assert data["total_findings"] == 0


def test_render_dispatches_format():
    rpt = _make_report()
    assert reporter.render(rpt, fmt="markdown").startswith("# PR Sentinel Report")
    assert json.loads(reporter.render(rpt, fmt="json"))["pr_title"] == "Test PR"
    # Unknown format falls back to markdown
    assert reporter.render(rpt, fmt="xml").startswith("# PR Sentinel Report")
