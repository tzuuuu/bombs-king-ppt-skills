---
name: pptgen
description: Generate visually unified, image-based presentation workspaces from articles, reports, papers, notes, or outlines. Use when the requested deliverable is full-slide PNGs or a Project Workspace for downstream editable-PowerPoint reconstruction.
metadata:
  openclaw:
    requires:
      bins:
        - python3
    primaryEnv: OPENAI_API_KEY
    envVars:
      - name: OPENAI_API_KEY
        required: false
        description: API key for CLI fallback.
      - name: OPENAI_BASE_URL
        required: false
        description: API base URL.
      - name: CODEX_PPT_IMAGE_MODEL
        required: false
        description: Image model, defaults to gpt-image-2.
      - name: CODEX_PPT_HOME
        required: false
        description: Runtime home override.
    homepage: https://github.com/ningzimu/codex-ppt-skill
---

# Codex PPT

Create complete 16:9 slide images and finish at a validated Project Workspace. Object-level editing belongs to the downstream reconstruction stage.

## Invariants

- **Producer boundary:** the confirmed image backend produces every final `origin_image/slide_XX.png`. Local drawing, Pillow, SVG, HTML/CSS/canvas, PowerPoint layout libraries, and manual overlays are invalid final-slide producers.
- **Backend lock:** the approved sample and every worker use the same backend, tool family, mode, and exposed model settings. Record these as `sample_generation_method`.
- **Terminal artifact:** deliver the Project Workspace and ordered Slide Image Set without an intermediate `.pptx`.

## Gate boundary protocol

- Execute every action inside the active Gate until its completion criterion is satisfied; do not pause for another user response or progress check inside the Gate.
- At a completed Gate, report its evidence and request one affirmative confirmation. For Gates 2–5, the outline, style, backend, or sample approval is this boundary confirmation.
- After one affirmative confirmation, start the next Gate and execute it uninterrupted through its own completion criterion. Pause only when a required input or blocker prevents completion, and report the evidence needed to resolve it.

## Gated Workflow

Run these gates in numbered order. Before creating artifacts or reporting progress, read `docs/workflow-gates-and-progress.md` for artifact barriers and the user-visible progress projection. A gate closes only on its stated evidence.

1. **Source gate — establish the brief.**
   Show a user-visible source brief that records topic, audience, goal, inclusions, exclusions, brand constraints, and page count; choose 8–12 slides when the user leaves count open. Add an asset inventory where each discovered asset records its source or path, intended role, and availability.
   **Complete when:** every brief field has an explicit value or a user-approved assumption, and every discovered asset has one inventory entry with all three fields. Any unresolved open question keeps this gate active.

2. **Outline gate — approve narrative and asset mapping.**
   Read `docs/outline-style-and-sample.md`, draft `outline.md` with page roles and required assets, show it to the user, and stop. When required assets exist, also read `docs/user-supplied-assets.md` and obtain approval for each slide-to-asset mapping.
   **Complete when:** the user approves the outline and every required-asset mapping; downstream final artifacts do not yet exist.

3. **Style gate — approve one visual system.**
   Follow the style branch in `docs/outline-style-and-sample.md`. Use a supplied direction directly after restating it; otherwise offer 2–3 concrete directions and recommend one. Keep identity fixed while varying composition by slide role.
   **Complete when:** the user approves one palette, typography direction, image language, density, and layout system.

4. **Backend gate — lock the producer.**
   Read `docs/backend-selection.md`, actively check built-in image-tool availability, explain the selected backend and fallback status, and request confirmation. Prefer the built-in tool. If CLI/API fallback is selected, read `docs/cli-api-fallback.md`; reach for `docs/image-model-configuration.md` only after a configuration error or an explicit settings request.
   **Complete when:** the user confirms one callable backend.

5. **Sample gate — approve one representative page.**
   Follow the sample branch in `docs/outline-style-and-sample.md`. Read `docs/project-handoff-and-reporting.md`, initialize the Project Workspace with `scripts/project_handoff.py init`, then generate exactly one representative `origin_image/slide_XX.png`. Show it, iterate on that same page, and record its approved `sample_generation_method` in `deck_spec.json`. Default to the current or source directory when no destination is given.
   **Complete when:** the user approves the page and the recorded method identifies the actual backend, tool, mode, prompt source, approved image, and available generation settings.

6. **Package gate — build reproducible inputs.**
   Prepare strict user assets per `docs/user-supplied-assets.md`. When the approved outline plans any Data Chart, read `docs/data-charts.md` and finish every Chart Source Package and the deck-level `chart_manifest.json` before prompt preparation. When page-scoped package, asset, or context tasks are independent, use subagents to parallelize all of them by page and fill every available slot; keep shared manifest assembly and validation in the parent.
   **Complete when:** `deck_spec.json` declares every planned page, every strict asset exists at its recorded path, and every delivered chart reproduces from its local snapshot.

7. **Production gate — prepare, dispatch, and record every page.**
   Read `docs/slide-generation-and-subagents.md` and `prompts/slide-worker.md`. Prepare self-contained slide jobs, then parallelize by filling every available dispatch slot with exactly one subagent per pending page; dispatch the next pending page immediately whenever a worker returns. Inspect returned candidates and record every outcome through the disclosed state contract.
   **Complete when:** `slide_job_status.py` shows every generated page as `recorded`, approved samples as `accepted`, and no page as `pending`, `dispatched`, or `blocked`.

8. **QA gate — inspect and repair the Slide Image Set.**
   Follow `docs/project-handoff-and-reporting.md`. Use one QA subagent per final page and fill every available slot; independent repair candidates may also run in parallel through the locked backend. The parent consolidates QA, selects replacements, and records the final state. For fallback editing commands, consult `docs/cli-api-fallback.md`.
   **Complete when:** every expected `slide_XX.png` passes the full checklist and rejected variants remain outside `origin_image/`.

9. **Handoff gate — validate the terminal artifact.**
   Finalize `outline.md` and, when requested, `speech.md` with `Slide N` headings. Run `scripts/project_handoff.py validate {base_dir}/{deck_name}` and use the final-report checklist in `docs/project-handoff-and-reporting.md`.
   **Complete when:** validation reports `ready_for_handoff`, requested notes exist, and the report names paths, counts, backend provenance, recorded status, regenerated or blocked pages, and known limitations.

## Conditional Branch

When the user asks to save a style, read `docs/style-library.md`. For a completed custom or adapted style, offer that action in the final handoff report. Personal styles live under `${CODEX_PPT_HOME:-~/.codex-ppt-skill}/references/` and override built-ins with the same filename.
