# Workflow Gates And Progress

Read this before creating downstream artifacts or reporting progress. `SKILL.md` owns the gate order and completion criteria; this reference owns artifact barriers and the user-visible projection of those gates.

## Gate boundary protocol

- Finish all planned actions inside the active Gate before requesting feedback; an in-Gate progress check is not a pause point.
- When its completion criterion is satisfied, report the evidence and request one affirmative confirmation. That confirmation unlocks the next Gate.
- After confirmation, execute the next Gate uninterrupted through its completion criterion. Pause only for a missing required input or a recorded blocker.

## Artifact Barriers

- Advance only after the active gate's completion criterion in `SKILL.md` is satisfied, unless the user explicitly skips that confirmation.
- Before outline approval, create no final `deck_spec.json`, `speech.md`, prompt job files, Chart Source Packages, slide images, or handoff state.
- If you need an internal planning artifact before approval, name it with `.draft.` such as `deck_spec.draft.json` or `speech.draft.md`, and clearly report that it is not final.
- Create downstream artifacts (`deck_spec.json`, `prompts/`, `slide_jobs.json`, Chart Source Packages, `chart_manifest.json`, `speech.md`, and final slide images) only at the gate that owns them.
- When the deck uses required source images, keep style selection and image generation behind approval of the slide-to-image mapping.
- If the user specifies a `.ppt` or `.pptx` master template, Gate 1 may create the source template package before outline approval: `template/template.pptx` or `template/template.ppt`, `template/template.pdf`, rendered `template/template-<N>.png` pages, and `template/template_manifest.json`. These are source/reference artifacts, not final slide images or an intermediate generated PPTX.

## Visible Progress Projection

For non-trivial decks, project the gate names from `SKILL.md` into a user-visible checklist with exactly one active gate. Mark a gate complete only from its `Complete when` evidence, and show blockers under the gate where they occurred.
