# 08 — Reach Windows feature parity

**What to build:** Run the same native render gate on Windows through PowerShell COM, including exact-target opening, safe rendering, cache identity, visible-slide artifacts, token verification, and inspection records. Supply a real-PowerPoint validation entrypoint suitable for a Windows host.

**Blocked by:** 05 — Record an evidence-sealed inspection; 06 — Fail closed on unsafe or ambiguous PowerPoint opens; 07 — Support the complete PowerPoint format matrix on macOS

**Status:** ready-for-agent

- [ ] Windows uses an isolated PowerPoint COM instance without requiring `pywin32` and leaves unrelated user presentations untouched.
- [ ] The Windows adapter satisfies the same JSON, artifact, mapping, cache, security, timeout, and inspection-record contracts as macOS.
- [ ] A smoke-test entrypoint exercises all nine approved formats on a Windows host with desktop PowerPoint.
- [ ] Mock and contract tests run without PowerPoint, while release validation remains pending until the real Windows matrix passes.
- [ ] Cross-platform cache validation refuses to reuse macOS artifacts on Windows or Windows artifacts from a different PowerPoint or font environment.
