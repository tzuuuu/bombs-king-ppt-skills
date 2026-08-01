# 04 — Finish PPTGen at Project Workspace handoff

**What to build:** Change PPTGen's user-visible completion path so a successful run ends with slide-image QA, Chart Source Package validation, and a Project Workspace handoff report rather than assembling an image-based PowerPoint file. Retain the approved outline, speaker script when expected, prompt jobs, state, and provenance while preserving all established approval and worker gates.

**Blocked by:** 01 — Establish the Project Workspace handoff CLI; 03 — Thread Data Charts through slide generation.

**Status:** ready-for-agent

- [ ] The orchestration contract describes a validated Project Workspace and Slide Image Set as PPTGen's terminal output.
- [ ] The final workflow phase performs complete slide QA and invokes handoff validation instead of PPTX assembly.
- [ ] Successful completion does not require or create an intermediate image-based PPTX.
- [ ] The speaker script remains available in the Project Workspace when expected but is not embedded into PowerPoint notes by PPTGen.
- [ ] The final report includes the Project Workspace, Slide Image Set, chart manifest, outline, speaker script availability, slide count, backend provenance, recorded-result status, regenerated or blocked slides, and known limitations.
- [ ] A run cannot be called complete when any slide is pending, dispatched, or blocked, or when any planned Data Chart lacks a valid Chart Source Package.
- [ ] Existing outline approval, style approval, backend confirmation, sample approval, subagent dispatch, result recording, and QA gates remain enforced.
- [ ] The Slide Image Set is documented as authoritative for layout and style, while Chart Source Packages are authoritative for Data Chart values.
- [ ] An end-to-end representative run with a Data Chart finishes at the handoff boundary and passes the black-box CLI acceptance seam without producing a PPTX.
