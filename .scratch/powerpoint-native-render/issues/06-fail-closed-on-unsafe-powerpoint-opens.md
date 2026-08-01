# 06 — Fail closed on unsafe or ambiguous PowerPoint opens

**What to build:** Ensure the native render gate opens only a trusted, saved, unambiguous snapshot and leaves the user's PowerPoint session unchanged. Unsafe sources and interactive blockers must return stable repair guidance without producing a valid cache entry.

**Blocked by:** 03 — Seal renders with exact-version caching

**Status:** ready-for-agent

- [ ] Sources already open in PowerPoint, quarantined or zone-marked files, passwords, repair prompts, Protected View, and other blocking dialogs stop before a valid render is published.
- [ ] Programmatic opens force-disable macros and disable external-link updates and network refreshes.
- [ ] macOS automation preserves unrelated presentations and the existing application; transient retries never force-quit the user's PowerPoint.
- [ ] Windows adapter contracts require a separately owned COM instance that can be closed without affecting other presentations.
- [ ] The default settle delay, bounded timeout, stable-output wait, and single classified transient retry behave consistently and expose stable error codes.
