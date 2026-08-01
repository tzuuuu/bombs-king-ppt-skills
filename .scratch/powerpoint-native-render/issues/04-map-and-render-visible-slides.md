# 04 — Map and render visible slides correctly

**What to build:** Give agents an inspection artifact set containing exactly the visible slides while preserving the untouched PowerPoint export as visual truth. Every derived page must retain an unambiguous mapping to its original slide number and stable PowerPoint slide identity.

**Blocked by:** 02 — Render one PPTX natively on macOS

**Status:** ready-for-agent

- [ ] Native exports containing all slides and exports already excluding hidden slides both normalize to one inspection PDF containing only visible slides.
- [ ] A native page count matching neither all slides nor all visible slides fails closed instead of guessing a mapping.
- [ ] PNG filenames use original slide numbers, and the manifest maps inspection PDF pages to original slide numbers and PowerPoint SlideIDs.
- [ ] A deck with no visible slides returns `NO_VISIBLE_SLIDES` and produces no inspection token.
- [ ] Speaker notes never appear in PDFs, PNGs, logs, manifests, or presence-by-slide metadata.
