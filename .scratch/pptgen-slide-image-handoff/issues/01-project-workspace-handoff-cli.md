# 01 — Establish the Project Workspace handoff CLI

**What to build:** Provide one user-facing command-line surface that initializes a Project Workspace and validates a complete slide-only handoff. A pipeline operator can initialize the expected workspace, place a complete Slide Image Set and its retained state inside it, run validation, and receive a clear handoff summary without generating an image-based PowerPoint file. Keep the existing assembly path available during this expansion ticket so the change can land independently.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Initialization creates the workspace collections required for slide images, prompt jobs, chart packages, and retained deck artifacts without creating a PPTX.
- [ ] A slide-only workspace with every expected slide image and accepted or recorded slide state passes validation.
- [ ] Successful validation reports the Project Workspace, Slide Image Set, slide count, retained outline and speaker-script availability, backend provenance, and recorded-result status.
- [ ] Validation rejects missing expected slide images, unexpected slide images, incomplete or blocked slide state, and missing required deck artifacts with actionable errors.
- [ ] Workspace inputs and reported artifact references cannot escape the Project Workspace.
- [ ] The command's initialization and validation behaviours are covered through black-box subprocess tests rather than private helper assertions.
- [ ] This ticket does not remove or change the existing assembly entry point.
