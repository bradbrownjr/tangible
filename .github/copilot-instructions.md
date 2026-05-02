# GitHub Copilot Instructions for Tangible

The canonical agent guide for this repo lives at [AGENTS.md](../AGENTS.md).
Read it on every session — it captures:

- Communication style (brief, action-over-explanation).
- Always/Never memory protocol (capture user directives as testable rules).
- Root-Cause Policy (never patch symptoms).
- **Regression Check Policy** (audit `git diff --stat` before every commit;
  written justification required for 200+ line single-file deletions).
- Commit & Release procedures (four version files + CHANGELOG + tag).
- Project layout, tech-stack versions, CI gates.
- Repo-specific gotchas (`.gitignore` source-package collisions, alembic in
  Docker image, loopback hosts in `allowed_hosts`, KSP1 fallback, slowapi
  callable bug, CSRF missing-Origin allowance, B008 ignore).
- Feature Registry — verify every relevant row survives any large refactor.

Never duplicate rules between this file and `AGENTS.md`. Update `AGENTS.md`
and let this pointer stay slim.
