# 02 — Render one PPTX natively on macOS

**What to build:** Make one normal `.pptx` travel through the complete macOS native-render path: snapshot the saved source, open that exact snapshot with desktop Microsoft PowerPoint, wait for layout to settle, export a native PDF, produce an inspection PDF and ordered PNG pages, and report the artifacts as versioned JSON.

**Blocked by:** 01 — Bootstrap the installable skill and diagnostic CLI

**Status:** resolved

- [x] A real macOS PowerPoint smoke test produces a valid native PDF, inspection PDF, page PNGs, and render manifest for a one-slide fixture.
- [x] The automation targets the snapshot by exact full path and closes only the presentation it opened.
- [x] The native PDF is retained unchanged, every derived page is traceable to it, and PowerPoint is the only slide renderer.
- [x] Settling, stable-PDF detection, DPI, timeout, absolute paths, and structured errors are externally observable through the CLI contract.

## Answer

Implemented the complete macOS path for a normal `.pptx`: source hashing, a verified immutable snapshot with a per-run filename, exact-path PowerPoint discovery, the 3-second settle gate, native PDF export, stable-PDF detection, unchanged native-PDF retention, inspection-PDF derivation, ordered 180-DPI PNG rasterization, versioned JSON, and exact-snapshot cleanup. PowerPoint 16.111.2 returns scripting error `-1750` for direct `save as PDF`, so the adapter falls back to PowerPoint's own accessible Export UI, selects a unique exact staging directory, waits for a complete PDF, then closes only the verified snapshot window. The render loop still performs at most one retry for a classified transient failure.

The final real smoke run used fixture source SHA-256 `8b65f122dc24bb5d9103aa4d8e99eaf52d11e604fe5f26d75706614bdb5a19fc` and produced one native PDF page, one inspection PDF page, one PNG, and `render.json`. The retained native PDF and inspection PDF both hashed to `bb9a81bc9b0dce5693ad9e9144cd592506cc10dafbdc0a0e801f99883218c91c`; the manifest hash matched, all artifact paths were absolute, and PowerPoint returned to its start screen. The fixture contains `SPEAKER_NOTES_MUST_NOT_APPEAR_9F3A` in speaker notes; extraction from the real native PDF confirmed the sentinel was absent, so notes were not exported.
