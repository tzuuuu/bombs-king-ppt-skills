# 03 — Seal renders with exact-version caching

**What to build:** Make repeated native renders safe and reusable by binding each cache entry to the exact requested source path, saved bytes, render environment, contract version, and derived-image settings. Concurrent agents must converge on one validated entry without observing partial artifacts.

**Blocked by:** 02 — Render one PPTX natively on macOS

**Status:** ready-for-agent

- [ ] Cache identity covers resolved source-path identity, source SHA-256, OS and architecture, PowerPoint version, installed-font fingerprint, contract version, and DPI.
- [ ] The source is hashed before and after snapshot creation, and only a hash-matching immutable snapshot can be exported.
- [ ] Cache hits are accepted only after full artifact validation; changes to any identity component invalidate reuse while preserving historical entries.
- [ ] Atomic staging and publication prevent partial cache reads, and competing writers are coordinated through a recoverable cross-platform lock.
- [ ] Cleanup previews the exact target, requires explicit confirmation, refuses active entries, and cannot target an ambiguous or global path.
