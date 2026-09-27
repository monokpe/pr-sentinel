# PR Sentinel Local — Handoff Brief (IBM Bob 2.0 Hackathon)

## Event context
- IBM Bob 2.0 Hackathon, lablab.ai, Sep 25–27, 2026 (48-hr build, kickoff 15:00 UTC Fri, submissions close 15:00 UTC Sun)
- $10k prize pool. Challenge brief not yet published (as of Sep 23) — v1's brief was open-ended ("build something using Bob to speed up dev work"), so plan for that pattern but confirm once the real brief drops
- Sponsor tech (Bob 2.0) needs to be a real, visible part of the build to qualify for prizes. Other tools can support it, but can't replace it as the core tech

## Concept
A local-first, privacy-conscious PR/code review agent built on IBM Bob 2.0.

Validated pattern: in v1, PRISM (PR Intelligent Semantic Monitor) placed top 5 by community votes — this problem space is proven to land with both judges and voters.

## Why this angle
- A very similar idea (PR Sentinel Local) was already scoped once before for a different hackathon — reuse the core thesis, adapt it to what Bob 2.0 actually offers
- Needs to read as a defensible, technical build, not a thin LLM wrapper — fits a multi-agent systems specialist positioning
- Python backend background (Django/FastAPI/Flask) — lean on that for implementation, not an unfamiliar stack

## Bob 2.0 features to actually exercise (not just namedrop)
- **Full repo context** — reasoning across the whole codebase, not just the diff
- **Subagents** — delegate parallel workstreams (e.g. one subagent flags security/quality issues, another checks consistency with the rest of the codebase, another drafts the human-readable review)
- **Plan Mode** — used to scope/triage before anything gets written, mirroring how a senior reviewer would approach a PR
- **MCP support** — pull external context (issue tracker, CI status) via MCP instead of hardcoding integrations

## What NOT to build
- Not "AI leaves comments on your PR" — that's the default everyone will ship
- Differentiator: local-first / privacy-conscious — review reasoning stays local, doesn't ship code to a third party; matters for regulated or IP-sensitive codebases
- Consider narrowing further: catching *semantic* regressions that full-repo context reveals but a line-diff-only linter would miss, rather than "general PR review"

## Demo requirements
- Live, end-to-end, under 3 minutes
- Show Bob doing something a line-diff reviewer genuinely couldn't do without full-repo context
- Show subagent delegation visibly on screen, not just described

## Constraints
- Solo build, no team currently
- 48-hour window, Sep 25–27, 2026
- Scope may need adjusting once the official challenge brief is published

## Open questions for Fable to help resolve
1. Concrete architecture — how do subagents hand off results to each other and to the final output?
2. MVP cut for a solo 48-hour build vs. nice-to-haves
3. The specific "aha" moment the demo script should build toward
4. Stack specifics — FastAPI service, CLI tool, or IDE/VS Code extension?
5. How to make "local-first" concrete and demonstrable on stage, not just a claim in the pitch
