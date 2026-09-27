# PR Sentinel

**Local-first, privacy-conscious PR review agent — powered by IBM Bob 2.0**

> Built for the IBM Bob 2.0 Hackathon (lablab.ai, Sep 25–27, 2026)

---

## What it does

PR Sentinel runs three specialist Bob subagents in parallel to review a pull request:

| Agent | Job |
|---|---|
| **SecurityAgent** | Hardcoded secrets, injection risks, missing auth |
| **ConsistencyAgent** | Semantic regressions only full-repo context can catch |
| **ReviewDrafterAgent** | Synthesises findings into a human-ready markdown review |

**The "aha" moment:** ConsistencyAgent reasons across the *entire* codebase — it catches a renamed config key still referenced by its old name in a caller, a broken function signature, or a new endpoint missing the auth pattern every other endpoint has. A line-diff linter can't do this.

**Privacy guarantee:** All inference runs locally via IBM Bob Desktop. Zero code leaves your machine.

---

## Quick start

```bash
# 1. Install
pip install -e .

# 2. Copy env template
cp .env.example .env
# edit .env if Bob is running on a non-default port

# 3. Check Bob is reachable
sentinel health

# 4. Review a real PR
sentinel review /path/to/repo --base main --head feature/my-branch --pr-title "My PR"

# 5. Run the mock demo (no git history needed)
python demo/run_mock_demo.py
```

---

## CLI reference

```
sentinel review [REPO_PATH]
  --base      Base branch/ref (default: main)
  --head      Head branch/ref (default: HEAD)
  --pr-title  Optional PR title
  --format    markdown | json  (default: markdown)
  --output    Write report to file

sentinel serve   # Start FastAPI server on http://127.0.0.1:8000
sentinel health  # Check Bob connectivity
```

## API

```bash
# Start server
sentinel serve

# Review via HTTP
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/repo", "base_ref": "main", "pr_title": "My PR"}'

# Health check
curl http://localhost:8000/health
```

---

## Architecture

```
CLI / API
    │
    ▼
OrchestratorAgent
    ├──► SecurityAgent     ┐
    │                      │  (parallel, ThreadPoolExecutor)
    └──► ConsistencyAgent  ┘
              │
              ▼
         ReviewDrafterAgent  (serial — needs prior results)
              │
              ▼
         ReviewReport  (markdown or JSON)
```

All agents talk to Bob via `bob_client.py` — a thin wrapper around the local
Ollama-compatible Bob Desktop API (`http://localhost:11434`).

---

## Demo

The `demo/` directory contains a synthetic Python "codebase" with four
intentional bugs planted in `demo_app/api.py`:

1. Hardcoded Stripe live API key → **SecurityAgent**
2. References `DATABASE_URL` after the PR renames it to `DB_CONNECTION_STRING` → **ConsistencyAgent**
3. `admin_delete_user` has no `require_auth()` call (every other endpoint does) → both agents
4. Calls `get_user(user_id)` but `utils.py` still imports the old config name → **ConsistencyAgent**

Run: `python demo/run_mock_demo.py`

---

_Inference is 100% local. Made with IBM Bob 2.0._
