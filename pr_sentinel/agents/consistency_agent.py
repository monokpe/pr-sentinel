"""
ConsistencyAgent — detects semantic regressions and cross-codebase inconsistencies.

This is the "aha" agent — it reasons across the FULL repo context to catch
things a line-diff linter cannot:
- A function signature changed here but callers elsewhere still use the old signature
- A new API endpoint is missing error handling that every other endpoint has
- A config key was renamed in this PR but old name is still referenced elsewhere
- A behaviour contract described in a docstring no longer matches the implementation
- A pattern used consistently across the codebase is violated in the new code
"""
from __future__ import annotations

from pr_sentinel import bob_client
from pr_sentinel.agents.utils import extract_json
from pr_sentinel.models import AgentResult, Finding, RepoContext, Severity

_VALID_SEVERITIES = {s.value for s in Severity}

AGENT_NAME = "ConsistencyAgent"

_SYSTEM_PROMPT = """\
You are ConsistencyAgent, a specialist subagent of PR Sentinel.
Your job is to find semantic regressions and inconsistencies that require reasoning
across the ENTIRE codebase — not just the changed lines.

A line-diff linter cannot catch these. You can, because you have full repo context.

Focus areas:
1. Callers of changed functions/methods that are now broken (wrong args, missing kwargs)
2. New code that violates patterns established everywhere else in the codebase
   (e.g. missing error handling, missing logging, different naming conventions)
3. Configuration keys, constants, or env vars renamed in the diff but still referenced
   with the old name elsewhere
4. Docstrings or comments that now contradict the updated implementation
5. New public API endpoints missing patterns present on all other endpoints
   (auth middleware, rate limiting, response schema)
6. Database schema or model changes that are inconsistent with related models

Respond ONLY with a valid JSON object matching this exact schema:
{
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "file": "<file path or empty string>",
      "line": <integer or null>,
      "title": "<short one-line title>",
      "detail": "<explanation — reference the specific other location that proves inconsistency>",
      "suggestion": "<concrete fix suggestion>"
    }
  ],
  "summary": "<1-2 sentence overall consistency summary>"
}

If there are no findings, return an empty findings array.
Do NOT include any text outside the JSON object.
"""


def _build_user_prompt(ctx: RepoContext) -> str:
    parts: list[str] = [
        f"## PR: {ctx.pr_title or '(no title)'}",
        f"Base branch: {ctx.base_branch}  →  Head: {ctx.head_branch}",
        "",
    ]
    focus = ctx.metadata.get("plan_review_focus", "")
    if focus:
        parts.append(f"## Plan Mode focus hint\n{focus}\n")

    parts.append("## Changed files (unified diff)")
    for fd in ctx.files_changed:
        parts.append(f"\n### {fd.path}  (+{fd.additions} -{fd.deletions})")
        parts.append("```diff")
        parts.append(fd.patch[:8000])
        parts.append("```")

    if ctx.full_file_contents:
        parts.append("\n## Full current source for ALL changed files (for cross-reference)")
        for path, source in ctx.full_file_contents.items():
            parts.append(f"\n### {path}")
            parts.append("```")
            parts.append(source[:8000])
            parts.append("```")

    return "\n".join(parts)


def run(ctx: RepoContext) -> AgentResult:
    """Run the consistency analysis and return an AgentResult."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(ctx)},
    ]

    raw = ""
    try:
        raw = bob_client.chat(messages, temperature=0.1)
        data = extract_json(raw)
        findings = [
            Finding(
                agent=AGENT_NAME,
                severity=Severity(f.get("severity", "info") if f.get("severity", "info") in _VALID_SEVERITIES else "info"),
                file=f.get("file", ""),
                line=f.get("line") if isinstance(f.get("line"), int) else None,
                title=f.get("title", ""),
                detail=f.get("detail", ""),
                suggestion=f.get("suggestion", ""),
            )
            for f in data.get("findings", [])
        ]
        return AgentResult(
            agent=AGENT_NAME,
            findings=findings,
            summary=data.get("summary", ""),
            raw_response=raw,
        )
    except Exception as exc:
        return AgentResult(
            agent=AGENT_NAME,
            raw_response=raw,
            error=str(exc),
        )
