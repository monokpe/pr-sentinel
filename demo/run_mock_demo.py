"""
Mock demo runner — exercises PR Sentinel without needing a real git history.

Builds a synthetic RepoContext from the demo_app files and feeds it
directly to the orchestrator, then prints the report.

Run from the repo root:
  python demo/run_mock_demo.py           # requires Bob Desktop running
  python demo/run_mock_demo.py --mock    # fully offline, no Bob required
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path

# Make sure the package is importable from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pr_sentinel import bob_client, orchestrator, reporter
from pr_sentinel.models import AgentResult, FileDiff, ReviewReport, RepoContext, Severity, Finding

console = Console()

# ---------------------------------------------------------------------------
# Synthetic diff — what the PR changes in api.py
# ---------------------------------------------------------------------------

DEMO_DIFF = """\
--- a/demo_app/api.py
+++ b/demo_app/api.py
@@ -1,8 +1,36 @@
-# api.py — original version (no user endpoints)
+# api.py — THIS IS THE FILE CHANGED IN THE DEMO PR
+
+from demo_app.config import DATABASE_URL
+from demo_app.auth import require_auth
+
+STRIPE_API_KEY = "DEMO_HARDCODED_KEY_replace_with_env_var"  # hardcoded secret! (demo fixture)
+
+
+def get_user(user_id: int, include_deleted: bool = False) -> dict:
+    conn = DATABASE_URL
+    return {"id": user_id, "deleted": include_deleted}
+
+
+def list_users(token: str, page: int = 1) -> list:
+    require_auth(token)
+    return paginate_results([], page)
+
+
+def paginate_results(items: list, page: int) -> list:
+    from demo_app.utils import paginate
+    return paginate(items, page)
+
+
+# New endpoint added in this PR — missing auth check!
+def admin_delete_user(user_id: int) -> dict:
+    user = get_user(user_id)
+    return {"deleted": user_id}
"""

DEMO_APP_ROOT = Path(__file__).parent / "demo_app"


def _read(rel: str) -> str:
    p = DEMO_APP_ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def build_demo_context() -> RepoContext:
    return RepoContext(
        repo_path=str(DEMO_APP_ROOT.parent),
        base_branch="main",
        head_branch="feature/add-user-endpoints",
        pr_title="Add user management endpoints",
        pr_description=(
            "Adds get_user, list_users, and admin_delete_user to api.py. "
            "Also renames DATABASE_URL → DB_CONNECTION_STRING in config."
        ),
        files_changed=[
            FileDiff(
                path="demo_app/api.py",
                additions=28,
                deletions=1,
                patch=DEMO_DIFF,
            )
        ],
        full_file_contents={
            "demo_app/api.py": _read("api.py"),
            "demo_app/config.py": _read("config.py"),
            "demo_app/auth.py": _read("auth.py"),
            "demo_app/utils.py": _read("utils.py"),
        },
    )


# ---------------------------------------------------------------------------
# Offline mock — pre-baked findings for --mock / presentation mode
# ---------------------------------------------------------------------------

def _build_mock_report(ctx: RepoContext) -> ReviewReport:
    """Return a hard-coded ReviewReport for offline/presentation use."""
    plan = AgentResult(
        agent="PlanAgent",
        summary=(
            "PR summary: Adds user management endpoints to api.py.\n"
            "Review focus: Scrutinise auth patterns on new endpoints and config rename blast-radius."
        ),
        raw_response=json.dumps({
            "pr_summary": "Adds get_user, list_users, and admin_delete_user to api.py; renames DATABASE_URL.",
            "areas_touched": ["demo_app/api.py", "demo_app/config.py"],
            "risk_areas": [
                {"area": "demo_app/api.py", "reason": "New write endpoint touches user deletion", "priority": "high"},
                {"area": "demo_app/config.py", "reason": "Config key rename may break callers", "priority": "high"},
            ],
            "red_flags": ["Touches auth layer", "Config rename across codebase"],
            "review_focus": "Scrutinise auth patterns on new endpoints and config rename blast-radius.",
        }),
    )

    security = AgentResult(
        agent="SecurityAgent",
        summary="1 critical finding: hardcoded live API key in api.py.",
        findings=[
            Finding(
                agent="SecurityAgent",
                severity=Severity.CRITICAL,
                file="demo_app/api.py",
                line=11,
                title="Hardcoded Stripe live API key",
                detail="STRIPE_API_KEY is committed in plaintext (hardcoded value). Live keys in source code are an immediate credential-leak risk.",
                suggestion="Remove the key, load it from an environment variable (os.getenv('STRIPE_API_KEY')), and rotate the leaked key immediately.",
            ),
            Finding(
                agent="SecurityAgent",
                severity=Severity.HIGH,
                file="demo_app/api.py",
                line=31,
                title="admin_delete_user has no authentication check",
                detail="Every other write endpoint calls require_auth(token) but admin_delete_user accepts user_id with no auth at all.",
                suggestion="Add require_auth(token) as the first line of admin_delete_user and add token to its signature.",
            ),
        ],
    )

    consistency = AgentResult(
        agent="ConsistencyAgent",
        summary="2 semantic regressions found that a line-diff linter would miss.",
        findings=[
            Finding(
                agent="ConsistencyAgent",
                severity=Severity.HIGH,
                file="demo_app/utils.py",
                line=3,
                title="utils.py still imports renamed config key DATABASE_URL",
                detail=(
                    "config.py is being renamed DATABASE_URL → DB_CONNECTION_STRING in this PR, "
                    "but utils.py line 3 still does `from demo_app.config import DATABASE_URL`. "
                    "This will raise ImportError at runtime — a pure diff of api.py wouldn't show this."
                ),
                suggestion="Update utils.py line 3: `from demo_app.config import DB_CONNECTION_STRING` and update its usage on line 9.",
            ),
            Finding(
                agent="ConsistencyAgent",
                severity=Severity.MEDIUM,
                file="demo_app/api.py",
                line=31,
                title="New endpoint violates auth pattern established by all existing endpoints",
                detail=(
                    "list_users and every other endpoint in api.py call require_auth(token) as their first action. "
                    "admin_delete_user does not. Full-repo context reveals this is a pattern break, not an oversight a linter would flag."
                ),
                suggestion="Follow the established pattern: add `token: str` parameter and call `require_auth(token)` first.",
            ),
        ],
    )

    drafter = AgentResult(
        agent="ReviewDrafterAgent",
        summary="Human-readable review drafted.",
        raw_response=(
            "## PR Review: Add user management endpoints\n\n"
            "**Verdict:** Request Changes\n\n"
            "### 🔴 Critical\n\n"
            "**Hardcoded Stripe live API key** (`demo_app/api.py:11`)  \n"
            "> `STRIPE_API_KEY` is committed in plaintext. Rotate this key immediately and load it via `os.getenv('STRIPE_API_KEY')` instead.\n\n"
            "### 🟠 High\n\n"
            "**admin_delete_user has no auth** (`demo_app/api.py:31`)  \n"
            "> Every other write endpoint calls `require_auth(token)` — this one doesn't. Add `token: str` to the signature and gate on it.\n\n"
            "**utils.py imports the old config key** (`demo_app/utils.py:3`)  \n"
            "> The rename `DATABASE_URL → DB_CONNECTION_STRING` in `config.py` breaks `utils.py` which still imports the old name. This is an `ImportError` at runtime — only visible with full-repo context.\n\n"
            "### 🟡 Medium\n\n"
            "**Pattern break on new endpoint** (`demo_app/api.py:31`)  \n"
            "> All existing endpoints share a consistent auth-first pattern. `admin_delete_user` violates it.\n\n"
            "### ✅ What's Good\n\n"
            "The `get_user` and `list_users` functions are clean and follow existing conventions well. "
            "The `paginate_results` helper is a nice abstraction. Once the security and consistency issues are fixed this will be a solid addition.\n"
        ),
    )

    all_findings = security.findings + consistency.findings
    return ReviewReport(
        repo_path=ctx.repo_path,
        pr_title=ctx.pr_title,
        total_findings=len(all_findings),
        critical_count=sum(1 for f in all_findings if f.severity == Severity.CRITICAL),
        high_count=sum(1 for f in all_findings if f.severity == Severity.HIGH),
        medium_count=sum(1 for f in all_findings if f.severity == Severity.MEDIUM),
        low_count=sum(1 for f in all_findings if f.severity == Severity.LOW),
        info_count=sum(1 for f in all_findings if f.severity == Severity.INFO),
        agent_results=[plan, security, consistency, drafter],
        human_review=drafter.raw_response,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="PR Sentinel mock demo")
    parser.add_argument(
        "--mock", action="store_true",
        help="Skip Bob entirely — use pre-baked findings for offline presentation"
    )
    args = parser.parse_args()

    console.print(
        Panel(
            "[bold cyan]PR Sentinel — Mock Demo[/bold cyan]\n"
            + ("[yellow]OFFLINE MODE[/yellow] — pre-baked findings, no Bob required\n" if args.mock else "")
            + "Repo context built from [green]demo/demo_app/[/green]\n"
            "PR: [yellow]feature/add-user-endpoints[/yellow] → [yellow]main[/yellow]",
            expand=False,
        )
    )

    ctx = build_demo_context()

    console.print(
        f"\n[dim]Loaded {len(ctx.files_changed)} changed file(s) + "
        f"{len(ctx.full_file_contents)} full-source file(s)[/dim]\n"
    )

    if args.mock:
        import time
        console.print("  [dim]🗺️   PlanAgent triaging PR (Plan Mode)...[/dim]")
        time.sleep(0.7)
        console.print("  [dim]✅  PlanAgent finished — PR summary: Adds user management endpoints.[/dim]")
        time.sleep(0.5)
        console.print("  [dim]🚀  Dispatching parallel specialist agents...[/dim]")
        time.sleep(0.8)
        console.print("  [dim]✅  SecurityAgent finished — 2 finding(s)[/dim]")
        time.sleep(0.4)
        console.print("  [dim]✅  ConsistencyAgent finished — 2 finding(s)[/dim]")
        time.sleep(0.6)
        console.print("  [dim]✍️   ReviewDrafterAgent synthesising human-readable review...[/dim]")
        time.sleep(0.8)
        console.print("  [dim]✅  ReviewDrafterAgent finished.[/dim]")
        report = _build_mock_report(ctx)
    else:
        if not bob_client.is_available():
            bob_url = os.getenv("BOB_API_URL", "http://localhost:11434")
            console.print(
                f"[red]⚠️  Bob is not reachable at {bob_url}[/red]\n"
                "Start Bob Desktop and re-run, or pass [bold]--mock[/bold] for offline mode."
            )
            sys.exit(1)

        def _log(msg: str) -> None:
            console.print(f"  {msg}")

        report = orchestrator.run(ctx, progress_cb=_log)

    rendered = reporter.render(report, fmt="markdown")

    console.print()
    console.print(Markdown(rendered))

    # Save report
    out = Path("reports")
    out.mkdir(exist_ok=True)
    (out / "demo_report.md").write_text(rendered, encoding="utf-8")
    console.print(f"\n[dim]Report saved to [bold]reports/demo_report.md[/bold][/dim]")

    sys.exit(1 if (report.critical_count or report.high_count) else 0)


if __name__ == "__main__":
    main()
