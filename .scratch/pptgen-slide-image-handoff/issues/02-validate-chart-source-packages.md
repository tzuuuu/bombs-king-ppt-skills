# 02 — Validate reproducible Chart Source Packages

**What to build:** Extend the Project Workspace handoff so every Data Chart can be delivered and verified as a reproducible Chart Source Package. The package contains the Python generator, exact local data snapshot, and transparent rendered chart, while the deck-level manifest associates it with the correct slide and semantic purpose. The managed runtime supplies the agreed chart libraries so delivered generators never install their own dependencies.

**Blocked by:** 01 — Establish the Project Workspace handoff CLI.

**Status:** ready-for-agent

- [ ] The managed runtime installs and can import Matplotlib, pandas, NumPy, and Seaborn.
- [ ] The chart manifest is versioned and uses only workspace-relative references.
- [ ] Every chart entry declares a unique chart identity, slide identity, chart type, semantic purpose, source description, Python generator, CSV or JSON snapshot, transparent render, and required-downstream status.
- [ ] Validation rejects missing package members, duplicate chart identities, unknown slide identities, absolute paths, and paths that escape the Project Workspace.
- [ ] Validation accepts two or more valid Chart Source Packages associated with one slide.
- [ ] The chart manifest does not accept or require coordinates, dimensions, bounding boxes, or downstream reconstruction instructions.
- [ ] A representative delivered chart generator recreates its render from its local snapshot without network access or package installation.
- [ ] The representative render has a transparent background and contains only the Data Chart's necessary axes, scales, legends, labels, units, and marks.
- [ ] The new chart-package success and failure cases are exercised through the black-box handoff CLI seam.
