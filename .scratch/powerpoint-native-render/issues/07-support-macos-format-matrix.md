# 07 — Support the complete PowerPoint format matrix on macOS

**What to build:** Extend the proven macOS native render gate from `.pptx` to every approved PowerPoint presentation, show, and template format while preserving the same evidence, safety, and visible-slide behavior.

**Blocked by:** 04 — Map and render visible slides correctly; 06 — Fail closed on unsafe or ambiguous PowerPoint opens

**Status:** ready-for-agent

- [ ] `.pptx`, `.pptm`, `.ppt`, `.ppsx`, `.ppsm`, `.pps`, `.potx`, `.potm`, and `.pot` each pass a real macOS PowerPoint render smoke test.
- [ ] Allowed extensions are verified against their OOXML ZIP or legacy OLE signatures, and mismatches fail before PowerPoint opens the source.
- [ ] Macro-enabled fixtures contain no macro code and render read-only with automation macros force-disabled.
- [ ] Shows and templates are rendered as presentation documents rather than starting playback or creating an untracked editable source.
- [ ] Unsupported and damaged formats return stable errors without publishing render artifacts.
