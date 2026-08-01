# Workflow Gates And Progress

Read this before creating downstream artifacts, advancing between phases, or reporting progress.

## Mandatory Phase Gates

This workflow has explicit approval gates. Do not advance to a later phase until the previous phase has been approved by the user, unless the user explicitly asks to skip that confirmation.

Phase order:

1. Source reading and asset extraction
2. Outline confirmation
3. Visual style confirmation
4. Image backend confirmation
5. One sample slide approval
6. Full slide generation
7. QA, speaker notes finalization, and Project Workspace handoff

Hard rules:

- Before outline approval, do not create final `deck_spec.json`, `speech.md`, prompt job files, Chart Source Packages, slide images, or handoff state.
- If you need an internal planning artifact before approval, name it with `.draft.` such as `deck_spec.draft.json` or `speech.draft.md`, and clearly report that it is not final.
- Downstream artifacts (`deck_spec.json`, `prompts/`, `slide_jobs.json`, Chart Source Packages, `chart_manifest.json`, `speech.md`, and final slide images) should be created only after the relevant gates have been approved.
- If the deck uses required source images, stop at outline confirmation and ask the user to verify the slide-to-image mapping before style selection or image generation.

## Visible Progress Plan

For non-trivial decks, keep a user-visible checklist with one active step:

1. Prepare source, outline, style, and backend decisions.
2. Generate and approve one sample slide.
3. Prepare slide jobs and slide state.
4. Dispatch slide subagents.
5. Record generated slide results.
6. QA, repair, notes, and Project Workspace handoff.

Completion evidence:

- `Prepare source, outline, style, and backend decisions`: `outline.md` is approved and image backend is confirmed.
- `Generate and approve one sample slide`: one final `origin_image/slide_XX.png` is approved as the style reference.
- `Prepare slide jobs and slide state`: `prompts/slide_XX.json`, `slide_jobs.json`, and `slide_run_state.json` exist.
- `Dispatch slide subagents`: `slide_job_status.py` shows dispatchable slides and each spawned worker is recorded by `record_slide_dispatch.py`.
- `Record generated slide results`: each worker output is recorded by `record_slide_result.py`, which copies the selected image into `origin_image/slide_XX.png` and records backend provenance.
- `QA, repair, notes, and Project Workspace handoff`: every expected final image exists, QA is complete, `speech.md` is final when expected, every planned Data Chart has a valid Chart Source Package, and `project_handoff.py validate` reports `ready_for_handoff`.

Do not mark a step complete just because the chat says it is complete; use real files or script-recorded state.
