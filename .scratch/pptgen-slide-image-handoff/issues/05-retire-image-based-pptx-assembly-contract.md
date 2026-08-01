# 05 — Retire the image-based PPTX assembly contract

**What to build:** Complete the contraction after every PPTGen workflow has migrated to Project Workspace handoff. Remove the obsolete image-based PowerPoint assembly surface and any dependency used only by it, then publish equivalent Chinese, English, and Korean documentation that consistently describes the new output contract, chart limitations, and final reporting behaviour.

**Blocked by:** 04 — Finish PPTGen at Project Workspace handoff.

**Status:** ready-for-agent

- [ ] No retained skill workflow, helper, prompt, or internal reference depends on the obsolete assembly entry point.
- [ ] The obsolete assembly entry point is removed after usage analysis confirms it is no longer needed.
- [ ] Any runtime dependency used only for image-based PowerPoint assembly is removed without affecting retained workflows.
- [ ] Repository READMEs and documentation sites in Chinese, English, and Korean describe the Project Workspace, Slide Image Set, Chart Source Packages, chart manifest, and absence of an intermediate PPTX equivalently.
- [ ] Examples, output trees, quickstarts, workflows, design notes, FAQs, capabilities, and limitations no longer promise PPTX assembly by PPTGen.
- [ ] The unreleased changelog records the user-visible workflow change in English and leaves the pull-request reference for the required follow-up.
- [ ] A repository-wide stale-contract search finds no active public or installable-skill claim that PPTGen completion produces or assembles an image-based PowerPoint file.
- [ ] The complete black-box handoff suite and existing slide-generation regressions pass after contraction.
- [ ] The final changed-file review preserves unrelated pre-existing workspace changes, including the existing style-reference deletion.
