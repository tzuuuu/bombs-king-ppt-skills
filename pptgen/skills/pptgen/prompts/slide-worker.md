# Slide Worker Prompt

Use this template when dispatching a slide subagent after the sample slide is approved and full-deck generation is authorized.

```text
Generate slide <N> for this pptgen deck.

Deck dir: <absolute deck dir>
Slide job file: <absolute deck dir>/prompts/slide_<NN>.json
Master template image selected by parent (when configured): <absolute deck dir>/template/template-<TEMPLATE_PAGE>.png
Candidate output directory owned by parent: <absolute deck dir>/generated_images/
Output target owned by parent: <absolute deck dir>/origin_image/slide_<NN>.png
Selected image backend: <built-in image tool OR CLI/API fallback>
Sample generation method copied from the approved sample:
- backend_used: <exact backend label recorded by parent>
- tool_name: <image_gen OR image_generate OR scripts/image_gen.py>
- mode: <generate OR edit>
- model/config: <model, size, quality, or "built-in default" if not exposed>
- prompt_source: <approved sample prompt source>
- input_context_preparation: <how local images were made visible or attached>
- approved_sample_path: <absolute path to approved origin_image/slide_XX.png>
- handoff_rule: use this same backend/tool/mode; return a blocker if unavailable
Input images already prepared by the parent:
- <absolute path> - approved sample slide style reference; match style only, do not copy layout
- <absolute path> - strict master template page when configured; preserve the rendered master background, margins, brand elements, placeholder regions, and lower-right page-number area
- <absolute path> - strict input asset; preserve labels/data/arrows/content

Read the JSON job file, then follow its `prompt` field exactly. Use the selected image backend and the recorded sample generation method only.
You must produce the final slide candidate by calling the selected image generation backend:
- Built-in mode: use the built-in image generation/editing tool.
- CLI/API fallback mode: use `scripts/image_gen.py` with the saved job prompt and required image inputs.
- Save or copy every original candidate image into `<absolute deck dir>/generated_images/` before returning. The parent agent only accepts a selected source from this directory.
- The parent agent copies the selected candidate into `origin_image/slide_<NN>.png`; do not write the final image there yourself.
- When the job contains `template_page`, use the prepared `template/template-<TEMPLATE_PAGE>.png` as the source of truth for the master background and layout. Preserve its visible structure and keep regions absent from it empty; the image model supplies slide content within that structure.

Forbidden for final slide image creation:
- local drawing or rendering scripts
- Pillow-generated slides
- SVG, HTML/CSS, or canvas screenshots
- python-pptx/PptxGenJS/native PPT layout screenshots
- manually composited text, card, chart, or image overlays

For every input marked as a Data Chart:
- use the supplied transparent chart render as required visual context in the complete page
- preserve its chart meaning and visual identity; do not invent replacement values
- do not edit its Chart Source Package or `chart_manifest.json`
- do not reserve a placeholder and do not locally composite the chart into the final slide

If you cannot use the selected image backend, stop and return `blocker=<reason>` instead of creating a lower-quality replacement.
If you cannot follow the recorded sample generation method, stop and return `blocker=<reason>` instead of switching tools.
Do not edit slide job files, Chart Source Packages, chart_manifest.json, origin_image, or speech.md. The parent validates the Project Workspace handoff and owns the copy from `generated_images/` into `origin_image/`.

Before returning, visually check:
- Chinese text is readable and not garbled
- style matches the approved sample slide
- master template background and visible layout elements match the supplied `template-<TEMPLATE_PAGE>.png`
- required source images are visibly included and not replaced by a similar redraw
- no overlapping or truncated important content
- no slide/page number is rendered; leave the lower-right page-number area available for downstream numbering

Return only:
backend_used=<built-in image tool OR scripts/image_gen.py>
selected_source=<absolute path to the selected candidate inside the deck's generated_images/ directory>
qa_note=<one sentence>
```
