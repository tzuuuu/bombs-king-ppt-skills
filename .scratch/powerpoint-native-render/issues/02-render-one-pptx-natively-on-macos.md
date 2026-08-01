# 02 — Render one PPTX natively on macOS

**What to build:** Make one normal `.pptx` travel through the complete macOS native-render path: snapshot the saved source, open that exact snapshot with desktop Microsoft PowerPoint, wait for layout to settle, export a native PDF, produce an inspection PDF and ordered PNG pages, and report the artifacts as versioned JSON.

**Blocked by:** 01 — Bootstrap the installable skill and diagnostic CLI

**Status:** ready-for-agent

- [ ] A real macOS PowerPoint smoke test produces a valid native PDF, inspection PDF, page PNGs, and render manifest for a one-slide fixture.
- [ ] The automation targets the snapshot by exact full path and closes only the presentation it opened.
- [ ] The native PDF is retained unchanged, every derived page is traceable to it, and PowerPoint is the only slide renderer.
- [ ] Settling, stable-PDF detection, DPI, timeout, absolute paths, and structured errors are externally observable through the CLI contract.
