"""
SecurityAgent — scans for security issues in the diff and full file context.

Looks for:
- Hardcoded secrets / credentials
- Dangerous function calls (eval, exec, shell injection, SQL injection patterns)
- Insecure deserialization
- Missing auth/permission checks on new endpoints
- Dependency changes that introduce known-risky packages
"""
from __future__ import annotations

from pr_sentinel import bob_client
from pr_sentinel.agents.utils import extract_json
from pr_sentinel.models import AgentResult, Finding, RepoContext, Severity

_VALID_SEVERITIES = {s.value for s in Severity}

AGENT_NAME = "SecurityAgent"

_SYSTEM_PROMPT = """\
You are SecurityAgent, a specialist subagent of PR Sentinel.
Your only job is to identify security vulnerabilities in the code changes provided.

Focus areas (check ALL of these):
1. Hardcoded secrets, API keys, passwords, tokens
2. Shell/command injection risks (subprocess, os.system, eval, exec)
3. SQL injection or unsafe query construction
4. Insecure deserialization (pickle.loads on untrusted input, yaml.load without Loader)
5. Missing authentication or authorisation on new routes/endpoints
6. Path traversal vulnerabilities
7. New dependencies with known risks

Respond ONLY with a valid JSON object matching this exact schema:
{
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "file": "<file path or empty string>",
      "line": <integer or null>,
      "title": "<short one-line title>",
      "detail": "<explanation of the issue>",
      "suggestion": "<concrete fix suggestion>"
    }
  ],
  "summary": "<1-2 sentence overall security summary>"
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
        parts.append(fd.patch[:8000])  # cap per-file diff to keep prompt sane
        parts.append("```")

    if ctx.full_file_contents:
        parts.append("\n## Full current source for changed files")
        for path, source in ctx.full_file_contents.items():
            parts.append(f"\n### {path}")
            parts.append("```")
            parts.append(source[:6000])
            parts.append("```")

    return "\n".join(parts)


def run(ctx: RepoContext) -> AgentResult:
    """Run the security analysis and return an AgentResult."""
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
