# PowerPoint Native Render Inspection Skill

Status: ready-for-agent

## Problem

Agents sometimes need to judge the visible content or appearance of a produced or supplied PowerPoint file. Object-model readers and alternative renderers do not reproduce Microsoft PowerPoint's font substitution, charts, masters, effects, and text layout reliably enough to serve as visual evidence.

The project needs an independently publishable skill that puts a **native render gate** before every such judgment. Passing the gate proves that the inspected pages came from the requested saved file, desktop Microsoft PowerPoint, and the recorded render environment. A failed gate stops the inspection.

## Deliverable

Create `powerpoint-native-render/` with one self-contained installable skill:

```text
powerpoint-native-render/
|-- README.md
|-- README_en.md
|-- LICENSE
|-- tests/
`-- skills/
    `-- inspect-powerpoint-natively/
        |-- SKILL.md
        |-- cli/
        `-- references/
```

The skill directory contains every runtime dependency declaration and resource it needs. Deployment consists of placing that directory in an OpenCode-compatible skill location and installing its CLI. OpenCode configuration and mandatory cross-skill invocation are separate deployment work.

## Skill Authoring Contract

### Invocation

Make `inspect-powerpoint-natively` model-invoked. The agent must reach it autonomously, and PPTGen or Image2Edit may reach it during later integration.

Use this description as the initial trigger contract, pruning only after invocation tests:

> Inspect visible PowerPoint content and appearance through native Microsoft PowerPoint rendering. Use when an agent needs to read or summarize visible slides, analyze presentation style or layout, use a PowerPoint file as a conversion or reconstruction reference, compare presentation visuals, or perform visual QA on a supported presentation, show, or template.

The branches are content review, style analysis, conversion/reconstruction reference, visual comparison, and visual QA. File copying, moving, renaming, hashing, delivery, and structure-only editing or validation do not cross the native render gate.

### Leading Word

Use **native render gate** throughout the skill. It means: no visible-content judgment begins until `render` and the first `verify` succeed, and no conclusion survives until `record-inspection` performs the second verification.

### Information Hierarchy

Give each rule one authoritative owner:

| Owner | Content |
| --- | --- |
| `SKILL.md` | Invocation, the four agent steps below, their completion criteria, the static-inspection boundary, and the final reporting rule |
| `references/inspection-policy.md` | Page-coverage branches, inspection-record meanings, supported-input boundary, and user-facing failure handling |
| `references/cli.md` | CLI installation check, command tree, syntax, and error recovery |
| `references/artifact-contract.md` | Cache identity, artifact layout, manifest/token fields, schemas, security invariants, and platform adapter contract |
| CLI implementation | Hashing, snapshots, locks, PowerPoint automation, retries, validation, atomic writes, filtering, rasterization, and cleanup enforcement |

`SKILL.md` points to a reference at the step where its branch becomes relevant. It does not restate reference lists, schemas, platform mechanics, or CLI option catalogs. References remain one level below `SKILL.md`.

### Agent Steps and Completion Criteria

1. **Define the inspection.** Identify the source, Project Workspace, purpose, and required visible-slide coverage. Read `references/inspection-policy.md` when selecting a coverage branch.
   - Complete when the source is a supported PowerPoint file, the workspace is explicit, the task purpose maps to one inspection scope, and unsupported dynamic or notes-only requests have been surfaced.
2. **Pass the native render gate.** Follow the pre-run check in `references/cli.md`, call `render`, then call `verify` for the same source and workspace.
   - Complete when both commands succeed and return one inspection token whose source, environment, manifest, PDF, page mapping, and PNG set all validate. Any failure ends the inspection with the CLI's repair action.
3. **Inspect the recorded scope.** View the PNG pages named by original slide number and record findings against those numbers. Increase DPI through the CLI when a page cannot be read reliably.
   - Complete when every slide required by the selected scope has been viewed at a legible resolution and each finding, no-finding result, and unverified dynamic element is accounted for.
4. **Seal the evidence.** Submit the token, scope, inspected slide numbers, and findings through `record-inspection`.
   - Complete when the command performs the second verification and writes a completed inspection record. Only `completion=complete`, `outcome=passed`, and coverage satisfying the task support a claim that QA passed.

### Static Boundary

The skill inspects static, non-hidden slide canvases. It records the presence of animations, transitions, audio, video, and interactive triggers without claiming to validate their behavior. Speaker notes are excluded from export, extraction, inspection, and reporting. A request whose success depends on dynamic behavior or speaker notes ends as unsupported.

## Runtime Contract

This section specifies the CLI behavior. Its detailed fields move once into `references/artifact-contract.md` during implementation; they are not copied into `SKILL.md`.

### Platforms and Inputs

- Run on macOS through desktop Microsoft PowerPoint and `osascript`.
- Run on Windows through desktop Microsoft PowerPoint and PowerShell COM; do not require `pywin32`.
- Return an unsupported-platform failure on Linux and headless environments.
- Accept `.pptx`, `.pptm`, `.ppt`, `.ppsx`, `.ppsm`, `.pps`, `.potx`, `.potm`, and `.pot`.
- Validate both the allowed extension and the underlying OOXML ZIP or legacy OLE signature.
- Stop on extension/signature mismatch, damage, passwords, repair prompts, Protected View prompts, unavailable automation permission, or other interactive blockers.

### Safe Open

- Treat the saved source bytes as authoritative. Require the user to save and close a source already open in PowerPoint.
- Detect macOS quarantine and Windows Zone.Identifier before snapshotting; return a repair action that asks the user to review the file manually.
- Hash the source, copy it to an immutable snapshot preserving its extension, verify the snapshot hash, then hash the source again.
- Force-disable macros immediately around every programmatic open.
- Open the snapshot read-only with external-link updates and network refreshes disabled.
- Address the opened snapshot by exact full path. Close only that snapshot on macOS; create and close an isolated COM instance on Windows.
- Preserve unrelated presentations and allow PowerPoint to launch or briefly take focus when native automation requires it.

### Render

- Export one slide per page at print/high-quality intent with no frame, handout layout, document properties, or PDF/A conversion.
- Prefer PowerPoint's visual-preservation fallback when a font cannot be embedded.
- Keep `powerpoint-export.pdf` unchanged as the native source of visual truth.
- Create `inspection.pdf` by removing whole hidden pages only when the native export contains them. A page-count mapping that matches neither all slides nor all visible slides fails validation.
- Exclude hidden slides and speaker notes from inspection artifacts. Return `NO_VISIBLE_SLIDES` when no visible slide exists.
- Rasterize `inspection.pdf` through PyMuPDF. Name PNG files by original slide number and map every inspection PDF page to the original slide number and PowerPoint SlideID.
- Wait 3 seconds after opening before export; allow `--settle-seconds` from 0 through 30.
- Wait for a stable, parseable PDF within a 180-second per-attempt timeout; allow 30 through 900 seconds.
- Retry one classified transient automation failure. Security, password, open-source, format, dialog, and source-mutation failures return immediately.
- Render PNG files at 180 DPI by default; allow 72 through 600 DPI and include DPI in derived-artifact identity.

### Cache and Concurrency

Store `.powerpoint-render-cache/` inside the caller-selected Project Workspace. A cache identity contains:

- normalized resolved source-path identity and source SHA-256;
- operating system and architecture;
- PowerPoint version and installed-font inventory fingerprint;
- render-contract version; and
- derived settings including DPI.

An entry contains the immutable snapshot, `powerpoint-export.pdf`, `inspection.pdf`, `render.json`, ordered PNG pages, and inspection records. Build it in a temporary directory and publish it atomically only after every hash, page, mapping, and schema validates.

Use one atomic cross-platform writer lock per cache identity. A competing writer waits for a bounded interval and validates the completed entry. Recover a stale lock only when its process is absent and its staged entry is incomplete. Preserve invalidated entries as history; reuse only an exact source-path, source-content, environment, contract, and derived-setting match.

### Verification and Records

`verify` re-hashes the current source and validates the environment, manifest, PDFs, mapping, and PNG set before issuing a token. `record-inspection` repeats those checks against the token. A mismatch invalidates the agent's intervening visual conclusion.

A completed record contains source and artifact identities, environment fingerprint, cache-hit status, task purpose, scope, inspected original slide numbers, excluded hidden slide numbers, both verification results, unverified dynamic elements, and findings.

Use these independent state axes:

- `completion`: `complete` or `blocked`;
- `outcome`: `passed`, `issues_found`, or `not_applicable`;
- `scope`: `all-visible-slides`, `selected-slides`, `style-sample`, or `content-review`; and
- `coverage`: inspected visible slides divided by all visible slides.

Logs and manifests contain identities and operational facts, not slide text, speaker notes, sensitive URLs, or full external-link targets.

### CLI Surface

```text
powerpoint-native-render doctor
powerpoint-native-render render <source> --workspace <dir>
powerpoint-native-render verify <source> --workspace <dir>
powerpoint-native-render record-inspection --token <token> ...
powerpoint-native-render clean --workspace <dir> --confirm
```

- `doctor` performs non-invasive dependency and environment checks.
- `doctor --automation-smoke-test --workspace <dir>` performs a real PowerPoint export and is required on first use and after an environment-fingerprint change.
- `render` creates or validates both PDFs and the PNG set.
- `verify` issues the pre-inspection token.
- `record-inspection` validates coverage and seals the post-inspection evidence.
- `clean` previews the exact cache target, requires confirmation, and refuses active entries.

Every command emits one versioned JSON object on stdout, diagnostics on stderr, absolute paths, stable error codes with repair actions, and a nonzero exit status for failure.

Install the self-contained Python CLI from `<skill-root>/cli` with `pipx`, documenting `uv tool` and user-site pip as fallbacks. Runtime commands do not install dependencies or create a project virtual environment.

## Inspection Coverage Reference

Move this branch table into `references/inspection-policy.md` during implementation:

| Purpose | Required visible slides |
| --- | --- |
| Whole-deck delivery QA | Every visible slide |
| Whole-deck summary | Every visible slide |
| Before/after comparison | Every changed slide plus slides affected by masters, themes, or global fonts |
| Style analysis | Cover, representative content, section, data-dense, and every distinct visual section |
| User-selected pages | Selected pages, expanded when the operation can affect other slides |

## Packaging and Documentation

- Initial version: `0.1.0` with versioned CLI, cache, manifest, token, and inspection-record schemas.
- License: MIT, `Copyright (c) 2026 tzuuuu`.
- Write `SKILL.md`, references, CLI help, JSON fields, error codes, source, and tests in English.
- Provide equivalent Traditional Chinese `README.md` and English `README_en.md` at package root; keep README files outside the installable skill.
- Validate the skill with the standard skill validator and prove that its directory has no dependency on repository-root files.
- Leave OpenCode configuration, PPTGen, Image2Edit, ZIP packaging, installers, release tags, and public release for later work.

## Acceptance Tests

- Exercise the CLI through exit codes, JSON output, and filesystem artifacts as the black-box acceptance seam.
- Cover all allowed extensions and signatures, cache identities, schemas, tokens, page maps, locks, atomic publication, cleanup guards, and stable error codes.
- Prove that mutation before, during, or after inspection cannot produce a completed record for stale artifacts.
- Cover cache hits and invalidation by path, content, OS, PowerPoint, font inventory, contract version, and DPI.
- Cover hidden-page filtering, original-slide filenames, all-hidden input, artifact hashes, PDF page counts, and PNG counts.
- Cover macro disablement, external-link suppression, security-marker and open-source blocking, timeouts, one retry, and application isolation.
- Run all nine formats against desktop PowerPoint on macOS.
- Provide a Windows smoke-test entrypoint and require all nine formats to pass on a Windows host with desktop PowerPoint before release. Mocks do not satisfy this release gate.
- Keep macro-enabled fixtures free of macro code; they test safe handling of the container format only.
- Mark the implementation release-validation-pending until the Windows matrix passes.

## Out of Scope

- OpenCode deployment configuration or mandatory invocation enforcement.
- Integration pointers in PPTGen or Image2Edit.
- Linux or headless rendering and alternative rendering engines.
- Speaker notes, hidden-slide inspection, and dynamic-behavior QA.
- Editing, repairing, refreshing, unblocking, password entry, or saving the user's source.
- ZIPs, installers, release tags, and public release.
- Moving, deleting, or committing the root `pptx_to_pdf_for_qa.py` reference prototype.

## Reference Prototype

Keep the root `pptx_to_pdf_for_qa.py` untouched and outside this feature's commits. Reuse its native-export, PDF-stability, JSON-output, and rasterization concepts. Replace its `last presentation` target selection and non-versioned output behavior with the contracts above.
