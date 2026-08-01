# 05 — Record an evidence-sealed inspection

**What to build:** Complete the native render gate by issuing a pre-inspection token and sealing the agent's findings only after a second exact-version verification. The completed record must distinguish finishing an inspection from passing QA and must prove that the inspected scope satisfies the task.

**Blocked by:** 03 — Seal renders with exact-version caching; 04 — Map and render visible slides correctly

**Status:** ready-for-agent

- [ ] Verification validates the current source, environment, manifest, PDFs, page mapping, and PNG set before issuing a token.
- [ ] Recording repeats verification against that token and rejects missing, hidden, foreign, or stale inspected-slide claims.
- [ ] Source or environment mutation before, during, or after inspection prevents a completed record for the stale artifacts.
- [ ] Records independently capture completion, outcome, scope, coverage, findings, cache use, both verification results, and unverified dynamic elements.
- [ ] QA can be reported as passed only for a complete, passed record whose coverage satisfies the selected inspection branch.
