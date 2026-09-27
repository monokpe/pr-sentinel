"""
Demo fixture — a small fake Python "codebase" with intentional bugs.

This directory contains:
  demo_app/
    auth.py          — original auth module
    api.py           — API routes (the PR changes this file)
    utils.py         — shared utilities
    config.py        — config / constants

The PR diff (demo_pr.patch) introduces:
  1. A hardcoded API key  (SecurityAgent should catch it)
  2. A renamed config key used by the old name in api.py (ConsistencyAgent catches it)
  3. A changed function signature whose caller is broken  (ConsistencyAgent catches it)

Run the demo:
  cd <repo root>
  sentinel review demo/ --base HEAD~1 --head HEAD --pr-title "Add user endpoint"

Or use the mock runner that doesn't need a real git history:
  python demo/run_mock_demo.py
"""
