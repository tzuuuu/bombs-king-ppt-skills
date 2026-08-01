# User-Supplied Assets

Read this before using paper figures, screenshots, logos, or other non-chart assets that must appear in the deck.

When the user provides paper figures, screenshots, logos, or other assets that must appear in the deck, treat them as source assets, not as loose visual inspiration.

Data Charts use the structured-data branch in `data-charts.md`; they are not image-only user-supplied assets.

## Master Template Branch

When the user supplies a PowerPoint master template, treat it as a required source asset and process it during Gate 1 before outline confirmation:

```bash
python3 {skill_root}/scripts/project_handoff.py init {base_dir}/{deck_name}
python3 {skill_root}/scripts/prepare_template.py \
  {source_template.pptx_or_ppt} \
  {base_dir}/{deck_name} \
  --overwrite
```

The command copies the source to `template/template.pptx` or `template/template.ppt`, exports it to `template/template.pdf`, renders each PDF page to `template/template-1.png`, `template/template-2.png`, and so on, and records the package in `template/template_manifest.json`. Inspect the rendered template pages and record the intended page mapping in the source brief and later `deck_spec.json`.

When preparing slide prompts, use the selected `template/template-<N>.png` as a strict input image. Preserve the visible master background, margins, brand elements, placeholder regions, and reserved lower-right page-number area. Treat regions absent from that PNG as intentionally empty so the image model supplies slide content within the supplied master structure.

Record the selected default and per-slide pages in `deck_spec.json`:

```json
{
  "template": {
    "source": "template/template.pptx",
    "pdf": "template/template.pdf",
    "rendered_pages": [
      "template/template-1.png",
      "template/template-2.png"
    ],
    "default_page": 1
  },
  "slides": [
    {"number": 1, "template_page": 1},
    {"number": 2, "template_page": 2}
  ]
}
```

If a slide does not specify `template_page`, `prepare_slide_prompts.py` uses `template.default_page`, then page 1. A prepared template page is automatically added to that slide's `reference_inputs` and `input_images` in `prompts/slide_XX.json`.

Recommended project-local asset location:

```text
{base_dir}/{deck_name}/assets/
├── figures/
│   ├── result_01.png
│   └── result_02.png
└── logos/
    └── lab_logo.png
```

Do not place source assets in `origin_image/`; that directory is only for final `slide_XX.png` images.

For slides that must include a user-supplied figure:

- Record the exact asset path or attachment name in `outline.md` for that slide, preferably as a Markdown image reference inside that slide's `Required images` list, then ask the user to confirm the mapping before generation.
- Stay on the already selected image backend. Do not switch between built-in image generation and CLI/API fallback only because a slide includes source images.
- Use the selected backend's reference-image or edit capability when available, with the supplied figure visible as an input image.
- In built-in `image_gen` mode, every source image must be visible in the conversation context before generating any slide that depends on it. User attachments and images generated earlier in the thread already qualify. For local image paths, inspect each required image with `view_image` first, then generate or edit the slide.
- In built-in `image_gen` mode, `view_image` is the required way to make local image paths visible to the conversation before generation. It is not a filename parameter to `image_gen`; the generation prompt must still label the visible image by role, such as `Image 1: strict input asset` or `Image 2: approved sample slide style reference`.
- Ask the model to preserve the supplied figure's data, labels, axes, colors, and visual content, and only compose the surrounding slide layout, title, captions, callouts, and background.
- Do not ask the model to redraw or invent numerical Data Charts. Use the accurate Chart Source Package render as required visual context.
- After generation, inspect the output and ask the user to pay special attention to whether required figures were used correctly.

Example prompt fragment for a result-figure slide:

```json
{
  "source_assets": [
    {
      "path": "{base_dir}/{deck_name}/assets/figures/result_01.png",
      "usage": "embed as the main evidence figure",
      "fidelity": "preserve the figure content; do not redraw or change data, axes, labels, colors, curves, bars, or legends"
    }
  ],
  "visual_elements": {
    "main_visual": "place the supplied result_01.png as a large figure panel, with a short caption and two callouts around it"
  },
  "constraints": [
    "Use the provided figure as an input image, not as a loose style reference.",
    "Do not synthesize a replacement chart.",
    "Keep all numerical values and labels in the supplied figure unchanged."
  ]
}
```
