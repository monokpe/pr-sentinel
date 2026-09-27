"""
OrchestratorAgent — coordinates parallel subagent execution and merges results.

Architecture:
  1. Ingest diff + full repo context  (ingestion.py)
  2. PlanAgent triages the PR (Plan Mode — serial, fast)
  3. Dispatch SecurityAgent and ConsistencyAgent concurrently  (ThreadPoolExecutor)
  4. Merge structured findings
  5. Dispatch ReviewDrafterAgent with merged findings
  6. Return a final ReviewReport
"""
from __future__ import annotations

import concurrent.futures
import json
from typing import Callable

from pr_sentinel.models import AgentResult, Finding, RepoContext, ReviewReport, Severity
from pr_sentinel.agents import security_agent, consistency_agent, review_drafter_agent, plan_agent


def _count_by_severity(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {s.value: 0 for s in Severity}
    for f in findings:
        counts[f.severity.value] += 1
    return counts


def _extract_review_focus(plan_result: AgentResult) -> str:
    """Pull the review_focus string out of the PlanAgent's JSON response."""
    try:
        data = json.loads(plan_result.raw_response)
        return data.get("review_focus", "")
    except Exception:
        return ""


def run(
    ctx: RepoContext,
    progress_cb: Callable[[str], None] | None = None,
) -> ReviewReport:
    """
    Orchestrate all subagents and return a completed ReviewReport.

    Parameters
    ----------
    ctx:
        Populated RepoContext from ingestion.load_repo_context().
    progress_cb:
        Optional callback called with status strings as work progresses.
        Used by the CLI to print live progress.
    """

    def _log(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    # ── Step 1: Plan Mode triage ──────────────────────────────────────────
    _log("🗺️   PlanAgent triaging PR (Plan Mode)...")
    plan_result = plan_agent.run(ctx)
    if plan_result.error:
        _log(f"⚠️   PlanAgent errored (continuing without plan): {plan_result.error}")
    else:
        _log(f"✅  PlanAgent finished — {plan_result.summary}")

    review_focus = _extract_review_focus(plan_result)

    # Inject the plan's focus hint into the repo context metadata so agents
    # can surface it in their prompts without a circular dependency.
    ctx.metadata["plan_review_focus"] = review_focus

    # ── Step 2: Parallel specialist agents ────────────────────────────────
    _log("🚀  Dispatching parallel specialist agents...")

    parallel_agents: list[tuple[str, Callable[[RepoContext], AgentResult]]] = [
        ("SecurityAgent", security_agent.run),
        ("ConsistencyAgent", consistency_agent.run),
    ]

    parallel_results: list[AgentResult] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(fn, ctx): name
            for name, fn in parallel_agents
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                status = f"✅  {name} finished — {len(result.findings)} finding(s)"
                if result.error:
                    status = f"⚠️   {name} errored: {result.error}"
            except Exception as exc:
                result = AgentResult(agent=name, error=str(exc))
                status = f"⚠️   {name} raised an exception: {exc}"
            parallel_results.append(result)
            _log(status)

    # Merge all findings
    all_findings: list[Finding] = []
    for r in parallel_results:
        all_findings.extend(r.findings)

    counts = _count_by_severity(all_findings)

    # ── Step 3: Review drafter ────────────────────────────────────────────
    _log("✍️   ReviewDrafterAgent synthesising human-readable review...")
    drafter_result = review_drafter_agent.run(ctx, parallel_results)
    if drafter_result.error:
        _log(f"⚠️   ReviewDrafterAgent errored: {drafter_result.error}")
    else:
        _log("✅  ReviewDrafterAgent finished.")

    all_results = [plan_result] + parallel_results + [drafter_result]

    return ReviewReport(
        repo_path=ctx.repo_path,
        pr_title=ctx.pr_title,
        total_findings=len(all_findings),
        critical_count=counts.get("critical", 0),
        high_count=counts.get("high", 0),
        medium_count=counts.get("medium", 0),
        low_count=counts.get("low", 0),
        info_count=counts.get("info", 0),
        agent_results=all_results,
        human_review=drafter_result.raw_response,
    )
