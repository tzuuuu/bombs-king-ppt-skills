# 09 — Harden the independently publishable skill

**What to build:** Finish a lean, predictable, independently deployable skill whose instructions, references, CLI, tests, and bilingual package documentation agree on one native render gate. The installed skill must be usable without repository-root files while leaving OpenCode and upstream skill integration for later.

**Blocked by:** 05 — Record an evidence-sealed inspection; 07 — Support the complete PowerPoint format matrix on macOS; 08 — Reach Windows feature parity

**Status:** ready-for-agent

- [ ] `SKILL.md` contains the approved model-invoked description, leading word, four agent steps, completion criteria, static boundary, and final reporting rule without duplicating reference contracts.
- [ ] The inspection policy, CLI manual, and artifact contract each own their assigned rules once and remain one context-pointer level below the skill.
- [ ] Traditional Chinese and equivalent English package documentation cover installation, platform requirements, limitations, and the Windows release gate.
- [ ] MIT licensing names `tzuuuu`, package and schema versions begin at `0.1.0` and `1`, and standard skill validation passes.
- [ ] Black-box tests cover the documented CLI surface and prove the installable skill directory has no dependency on repository-root files.
- [ ] The work produces no OpenCode configuration changes, PPTGen or Image2Edit integration edits, ZIP, installer, release tag, or public release.
