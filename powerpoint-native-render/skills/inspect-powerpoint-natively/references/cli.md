# CLI Reference

## Install

Install the self-contained CLI from this skill's `cli` directory with `pipx`:

```bash
pipx install ./cli
```

Use `uv tool install ./cli` when `pipx` is unavailable. Use a user-site pip installation only when neither tool is available. Do not install dependencies during a runtime command.

## Diagnose

Run the non-invasive prerequisite check without opening PowerPoint:

```bash
powerpoint-native-render doctor
```

Treat exit code `0` and `status: "ok"` as prerequisite evidence only. Treat `automation_permission.state: "unverified"` as a requirement to pass a real render smoke test before inspection.

## Render on macOS

Save and close a normal `.pptx`, choose its Project Workspace, and run:

```bash
powerpoint-native-render render /absolute/path/deck.pptx \
  --workspace /absolute/path/project-workspace \
  --settle-seconds 3 \
  --timeout 180 \
  --dpi 180
```

Use `--settle-seconds` from 0 through 30, `--timeout` from 30 through 900 seconds per attempt, and `--dpi` from 72 through 600. Expect at most one retry for a classified transient failure.

On success, use the absolute paths in the versioned JSON response to locate the immutable snapshot, unchanged `powerpoint-export.pdf`, `inspection.pdf`, ordered PNG pages, and `render.json`. Do not inspect or claim anything from those artifacts until the later `verify` command succeeds.

On failure, follow `repair_action` and stop. Never accept a stale PDF, an interactive PowerPoint prompt, an unclosed test snapshot, or an artifact path from a prior run as evidence for the requested source.

## Incomplete Command Surface

Treat the native render gate as unavailable for visual inspection until `verify` and `record-inspection` are installed. A successful `render` alone does not authorize visible-content judgment.
