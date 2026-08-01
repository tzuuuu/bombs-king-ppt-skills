# Data Charts And Chart Source Packages

Read this when the approved outline plans a Data Chart. For a Data Chart on the selected sample page, complete its package and manifest entry during the Sample Gate before generating that sample. Complete all remaining packages during the Package Gate before prompt preparation.

Every Data Chart is generated during the task from structured data. An image-only chart is not a substitute for its source data.

## Chart Source Package

For each chart:

1. Save the exact data used in the run as a local CSV or JSON snapshot.
2. Write a self-contained `chart.py` that reads that local snapshot and writes `chart.png` beside the script.
3. Use only Matplotlib, pandas, NumPy, and Seaborn unless the user explicitly approves another dependency.
4. Reproduce the delivered render without package installation, live-data fetching, or mutable external sources.
5. Render a transparent PNG using the confirmed deck palette.

The Chart-only render contains data marks and the axes, scales, legends, units, and labels necessary to understand them. Slide titles, narrative explanation, page numbers, cards, borders, shadows, and decorative containers belong to the complete slide image.

## Manifest Contract

Record every package in deck-level `chart_manifest.json` with schema version `1`. Each entry includes:

- `slide_id`
- a deck-unique `chart_id`
- `chart_type`
- `semantic_purpose`
- `source_description`
- `required_downstream: true`
- workspace-relative `package.script`, `package.data`, and `package.image` paths

Placement coordinates, bounding boxes, dimensions, and downstream reconstruction strategies are outside this contract. PPTGen owns chart identity and provenance; downstream editable-PowerPoint reconstruction owns detection and placement.

Declare the matching `chart_id` under the target slide's `data_charts` list in `deck_spec.json`. Finish every planned package and manifest entry before running `prepare_slide_prompts.py`. The helper rejects missing, duplicate, unknown, unplanned, opaque, or out-of-workspace chart packages and adds each chart render to its slide job as required visual context.

## Generation Boundary

The image backend generates the complete slide from the chart render as required visual context. The worker preserves the package and its values while composing the complete page, without a reserved chart region or local overlay.

The Slide Image Set is authoritative for layout and style. Chart Source Packages are authoritative for numerical values and chart reproduction.
