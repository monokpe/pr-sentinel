"""
FastAPI application for PR Sentinel.

Endpoints:
  POST /review        — run a full review against a local repo
  GET  /health        — liveness check (also verifies Bob is reachable)
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pr_sentinel import bob_client, orchestrator, reporter
from pr_sentinel.ingestion import load_repo_context

app = FastAPI(
    title="PR Sentinel",
    description="Local-first PR review agent powered by IBM Bob 2.0",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    repo_path: str = Field(..., description="Absolute path to the local git repository")
    base_ref: str = Field("main", description="Base branch or commit ref")
    head_ref: str = Field("HEAD", description="Head branch or commit ref")
    pr_title: str = Field("", description="Optional PR title")
    pr_description: str = Field("", description="Optional PR description")
    output_format: str = Field("markdown", description="'markdown' or 'json'")


class HealthResponse(BaseModel):
    status: str
    bob_reachable: bool
    bob_url: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    bob_url = os.getenv("BOB_API_URL", "http://localhost:11434")
    return HealthResponse(
        status="ok",
        bob_reachable=bob_client.is_available(),
        bob_url=bob_url,
    )


@app.post("/review")
def review(req: ReviewRequest) -> dict:
    repo_path = Path(req.repo_path).resolve()
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail=f"Repo path not found: {repo_path}")

    try:
        ctx = load_repo_context(
            str(repo_path),
            base_ref=req.base_ref,
            head_ref=req.head_ref,
            pr_title=req.pr_title,
            pr_description=req.pr_description,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to read repo: {exc}")

    log_lines: list[str] = []
    report = orchestrator.run(ctx, progress_cb=log_lines.append)

    fmt = req.output_format if req.output_format in ("markdown", "json") else "markdown"
    rendered = reporter.render(report, fmt=fmt)

    return {
        "report": rendered,
        "progress_log": log_lines,
        "summary": {
            "total_findings": report.total_findings,
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "low": report.low_count,
            "info": report.info_count,
        },
    }
