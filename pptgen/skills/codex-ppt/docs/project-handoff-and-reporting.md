# Project Handoff And Reporting

Read this before initializing the Project Workspace, generating Data Charts, writing speaker notes, validating the handoff, or sending the final report.

## Project Workspace

Use this output structure:

```text
{base_dir}/{deck_name}/
├── origin_image/
│   ├── slide_01.png
│   └── ...
├── chart_assets/
│   └── slide_XX/
│       └── chart_YY/
│           ├── chart.py
│           ├── data.csv or data.json
│           └── chart.png
├── chart_manifest.json
├── prompts/
│   ├── slide_01.json
│   └── ...
├── slide_jobs.json
├── slide_run_state.json
├── deck_spec.json
├── outline.md
└── speech.md
```

If the user did not specify a destination, use the current working directory or the source file directory. Initialize the workspace with:

```bash
python3 {skill_root}/scripts/project_handoff.py init {base_dir}/{deck_name}
```

The initializer never creates a PPTX. `origin_image/` is the Slide Image Set and contains only final `slide_XX.png` images. Keep drafts and rejected candidates elsewhere.

## Data Charts And Chart Source Packages

Every Data Chart must be generated during the task from structured data. Do not accept an image-only chart as a substitute for its source data.

For each chart:

1. Save the exact data used in the run as a local CSV or JSON snapshot.
2. Write a self-contained `chart.py` that reads that local snapshot and writes `chart.png` beside the script.
3. Use only Matplotlib, pandas, NumPy, and Seaborn unless the user explicitly approves another dependency.
4. Do not install packages, fetch live data, or depend on mutable external sources inside the delivered generator.
5. Render a transparent PNG using the confirmed deck palette.
6. Include only chart marks and the axes, scales, legends, units, and labels necessary to understand the data.
7. Do not add the slide title, narrative explanation, page number, card, border, shadow, or decorative container.

Record every package in deck-level `chart_manifest.json` with schema version `1`. Each entry must include:

- `slide_id`
- `chart_id`
- `chart_type`
- `semantic_purpose`
- `source_description`
- `required_downstream: true`
- workspace-relative `package.script`, `package.data`, and `package.image` paths

Do not record coordinates, bounding boxes, dimensions, or downstream reconstruction strategy. PPTGen owns chart identity and provenance; the downstream editable-PowerPoint workflow owns chart detection and placement.

Declare the matching `chart_id` under the target slide's `data_charts` list in `deck_spec.json`. Run `prepare_slide_prompts.py` only after all planned Chart Source Packages and the manifest are complete. The helper rejects missing, duplicate, unknown, unplanned, opaque, or out-of-workspace chart packages and adds each chart render to its slide job as required visual context.

The image backend generates the complete slide. Do not reserve a chart placeholder or locally composite the accurate chart render into the final page. The Slide Image Set is authoritative for layout and style; Chart Source Packages remain authoritative for numerical values.

## Quality Check And Repair

Before handoff, inspect every slide image. Check:

- Text is readable and not garbled.
- Slide content matches the outline.
- Title and key points are not truncated.
- Visual style is consistent across slides.
- No page number appears unless the user requested one.
- Important elements do not overlap.
- Every required source image and Data Chart is visibly represented.

If a slide has severe text or layout issues, regenerate it with a more constrained prompt. If a slide is mostly correct but has a localized issue, use the selected backend's edit capability when available. In CLI/API fallback mode, use `scripts/image_gen.py edit` and replace the final slide only after validating the edited output.

Do not treat values visible inside the generative full-slide image as the numerical source of truth. Verify the independent Chart Source Package instead.

## Speaker Script

Make sure `outline.md` reflects the final confirmed deck outline. Do not recreate it from scratch here.

Create `speech.md` as presenter notes that a speaker can use directly. It remains a Project Workspace handoff artifact for downstream reconstruction; PPTGen does not embed it into a PowerPoint file.

For each slide, write only the spoken talk track directly under a heading that maps to the slide number:

```markdown
## Slide 1: {Title}

{Presenter talk track}
```

Choose one deck-level delivery style based on the audience and purpose, then adapt pacing by slide role. Lead with the claim, explain visuals in viewing order, add examples and implications instead of rereading visible text, and use natural transitions. For Chinese decks, write natural Chinese speaker-facing prose.

## Handoff Validation

Before validating, ensure every generated slide is `recorded`, every approved sample is `accepted`, and no slide is `pending`, `dispatched`, or `blocked`.

Run:

```bash
python3 {skill_root}/scripts/project_handoff.py validate {base_dir}/{deck_name}
```

Validation checks:

- required workspace directories and deck artifacts exist;
- every expected `slide_XX.png` exists and there are no extra final slide images;
- slide jobs and run state are complete;
- no intermediate PPTX exists;
- every planned Data Chart has exactly one valid manifest entry;
- every Chart Source Package contains a Python generator, CSV/JSON snapshot, and transparent PNG;
- chart paths are workspace-relative and remain inside `chart_assets/`;
- chart identities are unique and refer to known slides;
- the manifest contains no placement data.

Do not report the Project Workspace complete when validation fails.

## Final Report

Report:

- Project Workspace path
- Slide Image Set path
- `chart_manifest.json` path and chart count, when Data Charts exist
- `outline.md` path
- `speech.md` path, when present
- `slide_jobs.json` path
- Number of slides
- Confirmed image backend and recorded-result status
- Any slides that were regenerated, blocked, or still have known limitations
- The limitation that full-slide images are authoritative for layout/style while Chart Source Packages are authoritative for Data Chart values
- For custom or adapted styles, offer to save the style in the personal style library

## Prompting Principles

- Keep one global visual style fixed across the deck.
- Vary slide composition by page role; style consistency does not mean repeating one layout.
- Use concrete visual metaphors and diagrams rather than decorative filler.
- Keep text concise enough to remain readable in generated images.
- Treat required source assets and Data Chart renders as role-labelled inputs.
- Generate the complete slide with the selected image backend; never use local drawing or manual composition as a fallback.
