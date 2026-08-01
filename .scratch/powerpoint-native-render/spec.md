# PowerPoint Native Render Inspection Skill

Status: ready-for-agent

## Problem Statement

The planned AI report-to-presentation system will generate slide images with PPTGen and reconstruct them as editable PowerPoint with Image2Edit. Agents may also need to inspect a produced or supplied PowerPoint file for content, style, comparison, or visual QA. Object-model readers and alternative renderers do not reproduce Microsoft PowerPoint's font substitution, native charts, masters, shadows, and text layout reliably enough to serve as visual evidence.

The project therefore needs a third, independently publishable skill that requires native desktop Microsoft PowerPoint to render supported files before an agent judges their visible content or appearance. The workflow must prove that inspected pages came from the exact requested source version, must not silently fall back to another renderer, and must remain deployable to OpenCode later without changing OpenCode configuration in this effort.

## Solution

Create an independent package rooted at `powerpoint-native-render/`. Its installable, self-contained skill will live at `skills/inspect-powerpoint-natively/` and include an agent-facing `SKILL.md`, a Python CLI package, references, and all runtime resources.

The CLI will copy the requested source into an immutable, content-addressed snapshot inside the caller's Project Workspace, open that snapshot read-only with desktop Microsoft PowerPoint, export a native PDF, validate it, remove hidden pages only when required, and rasterize the inspection PDF into ordered PNG pages. A versioned render manifest, environment-aware cache, inspection token, and before-and-after verification will prevent an agent from inspecting stale output and reporting it as the current file.

## Trigger Contract

The skill applies whenever an agent must use a supported PowerPoint file to make a judgment about visible presentation content or appearance, including:

- reading or summarizing visible slide content;
- analyzing layout, style, fonts, charts, images, or visual systems;
- using a PowerPoint file as conversion, reconstruction, or style-reference input;
- comparing presentation visuals before and after modification;
- performing visual QA or claiming that a presentation has been visually checked; and
- inspecting selected slides to decide a subsequent action.

The skill does not apply when an agent only copies, moves, renames, hashes, or delivers a file, or when it performs structural editing or validation without judging visible content. Structural tools may support file identity, editing, and slide mapping, but their output may not replace the Native PowerPoint Render as evidence that the presentation was seen.

## Supported Inputs and Platforms

- Support macOS with desktop Microsoft PowerPoint and `osascript`.
- Support Windows with desktop Microsoft PowerPoint and PowerShell COM automation.
- Fail closed on Linux, headless environments, missing PowerPoint, missing automation permission, or an unverified PowerPoint installation.
- Accept `.pptx`, `.pptm`, `.ppt`, `.ppsx`, `.ppsm`, `.pps`, `.potx`, `.potm`, and `.pot`.
- Reject `.ppam`, `.odp`, unknown extensions, extension/signature mismatches, damaged packages, passwords, repair prompts, Protected View prompts, and other interactive blockers.
- Verify both the extension and the underlying OOXML ZIP or legacy OLE signature before opening the file.

## Security and Application Isolation

- Open only an immutable snapshot and keep the original file unchanged.
- Refuse a source that is already open in PowerPoint; require the user to save and close it first.
- Treat the saved bytes on disk as the only source version. Never export unsaved application state.
- Detect macOS quarantine and Windows Zone.Identifier before copying. Do not remove, ignore, or bypass either security marker.
- Force-disable macros immediately around every programmatic open, including macro-enabled formats, and never run a macro.
- Disable external-link updates and network refreshes. Use only content already stored in the presentation; fail when reliable rendering requires an update or prompt.
- Operate on the exact presentation identified by its full path. Never select the active or last presentation as a proxy.
- Do not save or close unrelated presentations. On macOS close only the snapshot opened for the operation and do not quit an existing PowerPoint application. On Windows use and close an isolated COM instance.
- Permit PowerPoint to launch or briefly take focus when native automation requires it.

## Native Render and Inspection Artifacts

Use a caller-selected Project Workspace and store artifacts below `.powerpoint-render-cache/`. Never write cache artifacts beside the source or into the installed skill.

Each valid cache entry contains at least:

- a snapshot preserving the source extension;
- `powerpoint-export.pdf`, the untouched PDF exported by PowerPoint;
- `inspection.pdf`, containing only non-hidden slides;
- `render.json`, the versioned provenance and page-mapping manifest;
- ordered PNG pages named by original slide number, such as `slide-001.png` and `slide-003.png`; and
- completed inspection records.

PowerPoint remains the only slide renderer. PyMuPDF may validate the PDF, remove whole hidden pages without changing retained page content, and rasterize `inspection.pdf`; it must never reinterpret or reconstruct PowerPoint slide objects.

Speaker notes are excluded completely: do not export notes pages, generate notes images, extract notes text, or report which slides contain notes. Record only that speaker notes were excluded. Hidden slides are also excluded from the inspection PDF and PNG set. If all slides are hidden or the deck has no visible slides, fail with `NO_VISIBLE_SLIDES` and do not issue an inspection token.

The render manifest maps each PDF page to its original slide number and stable PowerPoint SlideID. Agent findings always identify the original slide number and may additionally report the inspection PDF page number.

## Rendering Settings

- Export one slide per PDF page with print/high-quality intent, no slide frame, no handout layout, no document properties, and no PDF/A conversion.
- Prefer visual preservation when fonts cannot be embedded, including PowerPoint bitmap fallback where available.
- Open the immutable snapshot, wait 3 seconds for fonts, charts, and text reflow, then export.
- Allow `--settle-seconds` from 0 through 30 and record the chosen value.
- Wait until the PDF size is stable across repeated checks and the file parses successfully.
- Use a default per-attempt timeout of 180 seconds, configurable from 30 through 900 seconds.
- Retry a classified transient automation failure at most once. Never retry security, password, source-open, format, dialog, or source-mutation failures automatically.
- Rasterize PNG pages at 180 DPI by default and allow an explicit 72-through-600 DPI value. Treat DPI as part of the derived-artifact identity.
- If small text cannot be inspected reliably, regenerate at a higher DPI instead of guessing.

## Cache Identity and Consistency

The cache identity includes:

- normalized resolved source-path identity;
- source-file SHA-256;
- operating system and architecture;
- Microsoft PowerPoint version;
- installed-font inventory fingerprint;
- render-contract version; and
- derived-image settings such as DPI.

Never share a cache entry across source paths, operating systems, PowerPoint versions, font environments, or incompatible contract versions. Preserve invalidated entries as historical evidence but never reuse them as current output.

Before export, hash the original, copy it into a new hash-specific staging area, verify that the snapshot hash matches, and hash the original again. Export only the immutable snapshot. Build an entry in a temporary directory and atomically publish it only after the PDF, page mapping, PNG set, hashes, and manifest all validate.

Use an atomic cross-platform writer lock for each cache identity. A competing render waits for a bounded interval and reuses the completed entry after validation. A stale lock may be recovered only when its process is absent and its staged entry is incomplete.

## Inspection Protocol

The required sequence is:

1. `render` creates or validates the native render and its derived pages.
2. `verify` re-hashes the current source and issues an inspection token containing the source, environment, and manifest identities.
3. The agent inspects the pages required by the task.
4. `record-inspection` repeats verification against the token before recording the conclusion.
5. If the source or environment changed at any point, discard the visual conclusion and start again.

Always export the complete deck, but inspect pages according to task purpose:

- whole-deck delivery QA inspects every non-hidden slide;
- a whole-deck summary inspects every non-hidden slide;
- before/after comparison inspects every changed slide and slides affected by global masters, themes, or fonts;
- style analysis covers the cover, representative content, section, and data-dense layouts plus any distinct visual section; and
- a user-specified page request may inspect only those pages unless the operation affects others.

The static PDF workflow does not validate animations, transitions, audio, video playback, or interactive triggers. Detect and record their presence without extracting content. A task explicitly requiring dynamic behavior verification must stop as unsupported rather than treating the static PDF as sufficient.

## CLI Contract

Provide these commands:

```text
powerpoint-native-render doctor
powerpoint-native-render render <source> --workspace <dir>
powerpoint-native-render verify <source> --workspace <dir>
powerpoint-native-render record-inspection --token <token> ...
powerpoint-native-render clean --workspace <dir> --confirm
```

- `doctor` performs non-invasive dependency and environment checks.
- `doctor --automation-smoke-test --workspace <dir>` performs a real PowerPoint export and is required on first use and whenever the environment fingerprint changes.
- `render` always produces both PDFs and the PNG page set.
- `verify` validates the current source, environment, artifacts, and mapping and returns an inspection token.
- `record-inspection` validates the token again, validates the declared inspected slide set, and atomically writes the completed inspection record.
- `clean` previews the exact workspace cache contents and requires explicit confirmation. It never targets a global or ambiguous path and refuses active entries.

All commands write one versioned JSON object to stdout, human-readable diagnostics to stderr, and use nonzero exit status for failure. JSON paths are absolute. Errors contain a stable `error_code`, a safe message, and a repair action. Logs and manifests do not contain slide text, notes, sensitive URLs, or full external-link targets.

Install the Python CLI from the self-contained skill directory:

```bash
pipx install --force --editable <skill-root>/cli
powerpoint-native-render doctor
```

Support `uv tool install` and user-site pip as documented fallbacks. Do not install dependencies during `render`, create a project virtual environment silently, or depend on files outside the installed skill directory. Use Python 3 and PyMuPDF; do not require `pywin32` because Windows automation runs through PowerShell COM.

## Inspection Record

A completed inspection record contains:

- source path identity and SHA-256;
- inspection token and render-manifest identity;
- operating system, PowerPoint version, and font fingerprint;
- native and inspection PDF paths and hashes;
- cache-hit status;
- task purpose and inspection scope;
- inspected original slide numbers and hidden slide numbers excluded from inspection;
- before- and after-verification results;
- dynamic content that was not verified; and
- findings or an explicit no-findings result.

Keep completion and outcome separate:

- `completion`: `complete` or `blocked`;
- `outcome`: `passed`, `issues_found`, or `not_applicable`;
- `scope`: `all-visible-slides`, `selected-slides`, `style-sample`, or `content-review`; and
- `coverage`: inspected visible slides divided by all visible slides.

An agent may claim that QA passed only when completion is `complete`, outcome is `passed`, both token verifications succeeded, and the recorded scope satisfies the user's task.

## Documentation and Packaging

- Package root: `powerpoint-native-render/`.
- Installable skill: `powerpoint-native-render/skills/inspect-powerpoint-natively/`.
- Initial package version: `0.1.0`.
- License: MIT, `Copyright (c) 2026 tzuuuu`.
- Write `SKILL.md`, CLI help, JSON fields, error codes, source, and tests in English.
- Provide a Traditional Chinese root `README.md` and equivalent English `README_en.md`.
- Keep runtime instructions in `SKILL.md` and one-level `references/`; do not place README files inside the installable skill.
- Do not produce a ZIP or installer in this effort.
- Do not modify OpenCode settings, project `AGENTS.md`, PPTGen, or Image2Edit in this effort.
- Do not claim that installing a discoverable skill alone guarantees invocation; mandatory OpenCode activation and cross-skill integration are later deployment work.

## Testing Decisions

- Exercise the CLI as the primary black-box acceptance seam through exit codes, JSON output, and filesystem artifacts.
- Unit-test all supported extensions, file signatures, cache identities, environment fingerprints, token validation, page maps, locking, atomic publication, cleanup guards, and stable error codes.
- Test source mutation before export, during export, before inspection, and after inspection; none may yield a valid completed record for stale artifacts.
- Test cache hits, source-path changes, OS/PowerPoint/font changes, DPI changes, incompatible schemas, stale locks, and concurrent writers.
- Test hidden-slide filtering, original-slide-number filenames, all-hidden input, native/inspection PDF hashes, PDF page counts, and PNG counts.
- Test macro disablement, external-link suppression, security-marker blocking, open-source blocking, timeouts, the one-retry limit, and application isolation.
- Run complete macOS integration tests against installed desktop PowerPoint for all nine supported formats.
- Supply a Windows smoke-test entrypoint and require all nine formats to pass on a Windows host with desktop PowerPoint before release.
- Macro-enabled fixtures contain no macro code; they prove only that macro-enabled containers render read-only with automation macros force-disabled.
- Mark the implementation as release-validation-pending until the Windows real-PowerPoint matrix passes; mocks alone cannot validate Windows support.
- Validate the finished skill with the standard skill validator and confirm the skill directory has no dependency on repository-root files.

## Out of Scope

- Implementing or modifying OpenCode deployment configuration.
- Adding mandatory trigger pointers to PPTGen or Image2Edit.
- Linux or headless rendering.
- LibreOffice, Keynote, Google Slides, or other rendering fallbacks.
- Speaker-note extraction, rendering, or QA.
- Hidden-slide inspection.
- Dynamic animation, transition, audio, video, or interactive-behavior QA.
- Editing, repairing, updating links, removing security markers, entering passwords, or saving the user's source file.
- Creating a ZIP, installer, release tag, or public release.
- Deleting or moving the root `pptx_to_pdf_for_qa.py` reference prototype.

## Further Notes

- The existing root `pptx_to_pdf_for_qa.py` is an untracked reference prototype and must remain untouched and outside this feature's commits.
- The future implementation should retain its useful native-export, PDF-stability, JSON-output, and optional rasterization ideas while replacing its `last presentation` target selection and non-versioned output behavior.
- OpenCode installation and invocation guarantees require a later deployment design because skills are loaded on demand; this package only supplies a self-contained, discoverable skill and deterministic runtime.
