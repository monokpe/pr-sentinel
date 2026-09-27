"""
ReviewDrafterAgent — synthesises all findings into a human-readable review.

Takes the structured output from SecurityAgent and ConsistencyAgent and
produces a polished markdown review that a human engineer could post as-is.
"""
from __future__ import annotations

from pr_sentinel import bob_client
from pr_sentinel.models import AgentResult, RepoContext

AGENT_NAME = "ReviewDrafterAgent"

_SYSTEM_PROMPT = """\
You are ReviewDrafterAgent, a specialist subagent of PR Sentinel.
You receive a list of findings from two specialist agents and your job is to
write a polished, human-readable code review that a senior engineer would be
proud to post.

Guidelines:
- Open with a brief overall verdict: Approve / Request Changes / Needs Discussion
- Group findings by severity (Critical → High → Medium → Low → Info)
- For each finding, be specific and actionable — cite the file and line where known
- Write in a collegial, direct tone — no corporate fluff
- Close with a short "What's good" paragraph acknowledging positive aspects of the PR
- Output ONLY the markdown review text, no JSON, no preamble

Format:
## PR Review: <pr title>

**Verdict:** <Approve | Request Changes | Needs Discussion>

### 🔴 Critical  (or omit section if none)
...

### 🟠 High
...

### 🟡 Medium
...

### 🟢 Low / Info
...

### ✅ What's Good
...
"""


def _serialise_findings(results: list[AgentResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(f"\n## Findings from {result.agent}")
        if result.error:
            lines.append(f"(agent errored: {result.error})")
            continue
        lines.append(f"Summary: {result.summary}")
        for f in result.findings:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            lines.append(
                f"- [{f.severity.upper()}] {f.title} ({loc})\n"
                f"  Detail: {f.detail}\n"
                f"  Suggestion: {f.suggestion}"
            )
        if not result.findings:
            lines.append("No findings.")
    return "\n".join(lines)


def run(ctx: RepoContext, prior_results: list[AgentResult]) -> AgentResult:
    """
    Produce a human-readable review from prior agent results.

    Parameters
    ----------
    ctx:
        The repo context (used for PR title, branch names).
    prior_results:
        Structured results from SecurityAgent and ConsistencyAgent.
    """
    user_content = (
        f"PR title: {ctx.pr_title or '(no title)'}\n"
        f"Base: {ctx.base_branch}  →  Head: {ctx.head_branch}\n"
        f"Description: {ctx.pr_description or '(none)'}\n"
        "\n--- Specialist agent findings ---\n"
        + _serialise_findings(prior_results)
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    raw = ""
    try:
        raw = bob_client.chat(messages, temperature=0.4)
        return AgentResult(
            agent=AGENT_NAME,
            summary="Human-readable review drafted.",
            raw_response=raw,
        )
    except Exception as exc:
        return AgentResult(
            agent=AGENT_NAME,
            raw_response=raw,
            error=str(exc),
        )
