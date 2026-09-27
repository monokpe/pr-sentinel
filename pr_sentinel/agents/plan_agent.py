"""
PlanAgent — Bob 2.0 Plan Mode triage step.

Runs BEFORE the specialist agents to:
  1. Summarise what the PR is actually trying to do
  2. Identify which areas of the codebase are touched
  3. Flag the highest-risk areas to guide specialist agent attention
  4. Produce a structured triage plan consumed by the orchestrator

This mirrors how a senior reviewer would spend 2-3 minutes skimming a PR
before diving into line-by-line review — and it makes Bob's Plan Mode
visible and meaningful in the demo.
"""
from __future__ import annotations

from pr_sentinel import bob_client
from pr_sentinel.agents.utils import extract_json
from pr_sentinel.models import AgentResult, RepoContext

AGENT_NAME = "PlanAgent"

_SYSTEM_PROMPT = """\
You are PlanAgent, operating in IBM Bob 2.0 Plan Mode.
Your job is to triage a pull request BEFORE any specialist review begins.

You do NOT look for specific bugs. Instead you:
1. Summarise what the PR is trying to accomplish (1-2 sentences)
2. List the areas of the codebase touched (files / modules / layers)
3. Identify the top 3 risk areas that deserve the most scrutiny
4. Flag any obvious red flags visible at a glance (e.g. "touches auth layer", "modifies DB schema")

Respond ONLY with a valid JSON object:
{
  "pr_summary": "<1-2 sentence summary of what this PR does>",
  "areas_touched": ["<area1>", "<area2>", ...],
  "risk_areas": [
    {
      "area": "<file or module name>",
      "reason": "<why this deserves scrutiny>",
      "priority": "high|medium|low"
    }
  ],
  "red_flags": ["<flag1>", "<flag2>"],
  "review_focus": "<one sentence directing specialist agents where to focus>"
}

Do NOT include any text outside the JSON object.
"""


def _build_user_prompt(ctx: RepoContext) -> str:
    parts = [
        f"## PR: {ctx.pr_title or '(no title)'}",
        f"Description: {ctx.pr_description or '(none)'}",
        f"Base: {ctx.base_branch}  →  Head: {ctx.head_branch}",
        "",
        f"## Files changed ({len(ctx.files_changed)} total)",
    ]
    for fd in ctx.files_changed:
        parts.append(f"- {fd.path}  (+{fd.additions} -{fd.deletions})")

    # Include diffs but keep this prompt lightweight — plan mode is fast
    parts.append("\n## Diffs (truncated)")
    for fd in ctx.files_changed:
        parts.append(f"\n### {fd.path}")
        parts.append("```diff")
        parts.append(fd.patch[:3000])
        parts.append("```")

    return "\n".join(parts)


def run(ctx: RepoContext) -> AgentResult:
    """Run plan-mode triage and return an AgentResult with the plan in raw_response."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(ctx)},
    ]

    raw = ""
    try:
        raw = bob_client.chat(messages, temperature=0.1)
        data = extract_json(raw)
        summary = (
            f"PR summary: {data.get('pr_summary', '')}\n"
            f"Review focus: {data.get('review_focus', '')}"
        )
        return AgentResult(
            agent=AGENT_NAME,
            summary=summary,
            raw_response=raw,
        )
    except Exception as exc:
        return AgentResult(
            agent=AGENT_NAME,
            raw_response=raw,
            error=str(exc),
        )
