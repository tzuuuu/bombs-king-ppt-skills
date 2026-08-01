# Require native PowerPoint rendering for presentation inspection

Agents must treat a PDF exported by desktop Microsoft PowerPoint as the visual source of truth whenever they need to judge the visible content or appearance of a supported PowerPoint presentation, show, or template. The independently publishable `inspect-powerpoint-natively` skill will enforce this on macOS and Windows and fail closed when native rendering cannot be proven; deterministic PDF processing may remove hidden pages and rasterize inspection pages but may not re-render slide content. This deliberately trades Linux and headless compatibility for fidelity to PowerPoint's handling of fonts, charts, masters, effects, and text layout.

## Consequences

The workflow requires installed desktop PowerPoint, immutable source snapshots, environment-aware cache validation, and inspection evidence tied to the exact source version. Skill installation alone cannot guarantee invocation, so OpenCode configuration and integration with the other presentation skills remain a separate deployment concern.
