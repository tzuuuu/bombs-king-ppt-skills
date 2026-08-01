# PPTGen Slide Image Handoff

Status: ready-for-agent

## Problem Statement

The current PPTGen workflow generates complete slide images and then assembles them into an image-based PowerPoint file. In the planned AI report-to-editable-PowerPoint system, that intermediate file is unnecessary: the next stage needs the ordered slide images, the resumable generation state, and reproducible sources for every numerically meaningful chart. Assembly also hides the fact that a generative image backend cannot guarantee accurate chart values inside a full-slide image.

The user needs PPTGen to stop at a well-defined Project Workspace handoff. The Slide Image Set must preserve the intended layout and visual style, while each Data Chart must have an independently reproducible Chart Source Package that remains authoritative for its values. The workflow must be machine-validatable and ready for a later editable-PowerPoint stage without defining that downstream stage here.

## Solution

PPTGen will finish by validating and reporting a complete Project Workspace instead of assembling a PowerPoint file. The workspace will retain the approved outline, deck specification, speaker script when expected, prompt jobs, run state, backend provenance, and ordered Slide Image Set.

Whenever a slide requires a Data Chart, the agent will generate that chart from structured data with the managed Python chart toolchain. It will deliver the exact data snapshot, the Python source, and a transparent rendered chart as a Chart Source Package. A deck-level chart manifest will associate every package with its slide and semantic purpose without prescribing its location in the finished slide.

The image backend will still generate each complete slide layout. It will receive the rendered Data Chart as required visual context, but no placeholder or deterministic local overlay will be introduced. The Slide Image Set is therefore authoritative for layout and style, while Chart Source Packages are authoritative for chart values.

A single project-handoff command-line interface will initialize and validate the workspace. Its black-box behavior will be the primary acceptance seam for the feature.

## User Stories

1. As a report-to-presentation user, I want PPTGen to stop after producing slide images, so that the editable-PowerPoint stage can consume them directly.
2. As a report-to-presentation user, I want PPTGen not to create an intermediate image-based PowerPoint file, so that the pipeline avoids an unnecessary container and conversion step.
3. As a user resuming an interrupted generation, I want the complete Project Workspace retained, so that approved decisions and completed slide work are not lost.
4. As a user reviewing generated work, I want slide images named and ordered consistently, so that page sequence is unambiguous.
5. As a downstream reconstruction agent, I want the Slide Image Set to represent the complete intended layouts, so that I can reconstruct the presentation from visible pages.
6. As a downstream reconstruction agent, I want the workspace to include the approved outline and deck specification, so that I can understand the intended narrative and slide roles.
7. As a downstream reconstruction agent, I want the speaker script retained when it was requested, so that it can be carried into the eventual presentation.
8. As a pipeline operator, I want prompt jobs and run state retained, so that I can audit or resume slide production.
9. As a pipeline operator, I want backend provenance retained, so that I can verify how the approved sample and remaining slides were generated.
10. As a viewer of a data-driven slide, I want every Data Chart to originate from structured data, so that its values have a verifiable source.
11. As a downstream reconstruction agent, I want the exact data snapshot used for each Data Chart, so that later changes to an API, database, or report cannot alter the historical result.
12. As a downstream reconstruction agent, I want the Python source used to render each Data Chart, so that I can reproduce its chart type and visual decisions.
13. As a downstream reconstruction agent, I want the rendered chart image included, so that I have a clear appearance reference.
14. As a user validating a chart, I want its data snapshot to be the numerical source of truth, so that generated full-slide image discrepancies do not silently replace correct values.
15. As a chart author, I want a standard managed chart toolchain, so that delivered scripts run consistently without installing their own packages.
16. As a chart author, I want additional chart libraries to require explicit approval, so that workspace dependencies remain controlled and reproducible.
17. As a presentation designer, I want Data Charts to use the confirmed deck palette, so that they fit the presentation's visual identity.
18. As a presentation designer, I want chart renders to have transparent backgrounds, so that their appearance is portable across slide designs.
19. As a presentation designer, I want chart renders to omit slide titles and narrative copy, so that chart generation stays separate from slide storytelling.
20. As a presentation designer, I want chart renders to omit cards, borders, shadows, and decorative containers, so that those elements remain part of the complete slide layout.
21. As a user, I want axes, scales, legends, units, and necessary labels preserved in chart renders, so that each chart remains understandable on its own.
22. As a user, I want all Data Charts created during the task from structured data, so that the workflow never fabricates reproducibility for an image-only chart.
23. As a slide-generation agent, I want the image backend to generate the complete page, so that no reserved chart placeholder changes the intended visual composition.
24. As a pipeline operator, I want local chart overlays and manual slide composition prohibited, so that full-slide generation keeps its existing image-backend-only boundary.
25. As a pipeline operator, I want a chart manifest that associates chart packages with slides, so that handoff does not depend on guessing from filenames.
26. As a pipeline operator, I want the chart manifest to support multiple charts on one slide, so that data-dense slides remain unambiguous.
27. As a downstream reconstruction agent, I want chart semantic purposes recorded, so that I can distinguish charts that may use similar data or visuals.
28. As a downstream reconstruction agent, I want chart placement excluded from the PPTGen contract, so that detection and placement remain the responsibility of the later stage.
29. As a pipeline operator, I want workspace-relative chart references, so that a Project Workspace can be moved without breaking its manifest.
30. As a pipeline operator, I want an initialization command that creates the required workspace structure without generating a PowerPoint file, so that every run starts consistently.
31. As a pipeline operator, I want a validation command that rejects missing chart scripts, snapshots, or renders, so that incomplete handoffs cannot be reported as complete.
32. As a pipeline operator, I want validation to reject unknown slide references and duplicate chart identities, so that manifest mistakes are caught before handoff.
33. As a pipeline operator, I want validation to accept multiple valid charts for one slide, so that legitimate layouts are not blocked.
34. As a user, I want completion to require every expected slide image and all accepted or recorded slide-job states, so that partial decks are not reported as finished.
35. As a user, I want the final report to identify the Project Workspace, Slide Image Set, chart manifest, outline, speaker script when present, slide count, backend, and limitations, so that I know exactly what was delivered.
36. As a maintainer, I want all supported documentation languages to describe the same output contract, so that users receive consistent instructions.
37. As a maintainer, I want the chart dependencies installed by the existing managed runtime, so that chart generation follows the skill's established setup path.
38. As a maintainer, I want existing sample approval, backend locking, subagent dispatch, result recording, and slide QA behavior preserved, so that this change does not weaken proven workflow gates.

## Implementation Decisions

- The skill's terminal artifact changes from an assembled image-based PowerPoint file to a validated Project Workspace.
- The existing Slide Image Set naming and ordering convention remains the content handoff for complete slide layouts.
- Speaker scripts remain workspace artifacts when expected, but PPTGen no longer embeds them into PowerPoint notes.
- The final workflow phase becomes slide-image QA, Chart Source Package validation, and workspace handoff reporting.
- A chart planning and generation phase occurs before full-slide generation whenever the approved outline includes Data Charts.
- Every Data Chart is created during the task from structured data. Image-only charts without underlying data are not an alternate workflow.
- Each Chart Source Package contains one Python generator, the exact CSV or JSON data snapshot used for the run, and one transparent PNG render.
- Chart generators read only their delivered local snapshot when reproducing the delivered result. They do not fetch live data, access the network, or install packages.
- The managed chart toolchain consists of Matplotlib, pandas, NumPy, and Seaborn. Any additional library requires explicit user approval.
- Chart renders include only data marks and the axes, scales, legends, units, and labels necessary to understand them.
- Chart renders exclude slide titles, narrative explanations, page numbers, cards, borders, shadows, and decorative containers.
- Chart renders use a transparent background and the confirmed deck palette.
- The image backend receives each relevant chart render as required visual context and generates the complete slide.
- No reserved chart region, deterministic chart overlay, manual compositing, or other local construction of the final slide image is introduced.
- The Slide Image Set is authoritative for layout and style. Chart Source Packages are authoritative for numerical values and chart reproduction.
- The chart manifest is a versioned deck-level contract using workspace-relative references.
- Every chart manifest entry records a unique chart identity, its slide identity, chart type, semantic purpose, source description, package members, and that the package is required downstream.
- The chart manifest supports multiple charts per slide and rejects duplicate chart identities or references to unknown slides.
- The chart manifest intentionally excludes coordinates, dimensions, bounding boxes, and downstream reconstruction strategies.
- One project-handoff command-line surface owns both workspace initialization and final handoff validation, replacing assembly as the highest-level runtime boundary.
- Handoff validation confirms slide completeness, accepted or recorded job states, chart-plan-to-manifest coverage, package existence, valid workspace-relative references, and manifest uniqueness.
- A handoff cannot be reported complete when any expected slide or required chart package is missing or when slide run state is incomplete.
- Existing sample approval, backend selection, subagent dispatch, result recording, and QA rules remain unchanged except where they previously required assembly.
- Assembly-only runtime code and dependencies may be removed after confirming that no retained workflow uses them.
- Public documentation and the changelog are updated as a user-visible workflow change, with all supported language variants kept equivalent.

## Testing Decisions

- The primary and only new high-level test seam is the project-handoff command-line interface, exercised as a black box through its externally observable exit status, output, and generated workspace artifacts.
- A good acceptance test describes a complete or invalid workspace from the user's perspective and avoids asserting private helper functions, internal class structure, or incidental implementation details.
- The initialization acceptance test verifies that a valid Project Workspace is created without producing a PowerPoint file.
- The successful handoff test uses a representative workspace containing ordered slide images, completed slide-job state, and at least one complete Chart Source Package.
- Failure cases cover missing slide images, incomplete slide-job state, missing Python source, missing data snapshots, missing chart renders, duplicate chart identities, unknown slide references, absolute or escaping manifest paths, and planned charts without manifest entries.
- A successful multi-chart test proves that two or more valid Chart Source Packages can target the same slide.
- A chart reproduction fixture proves that a delivered generator can recreate its PNG from its local snapshot with the managed chart runtime, without network access or package installation.
- The chart fixture verifies a transparent background and the agreed chart-only content boundary; visual-story text remains outside the fixture.
- Existing slide state and result-recording behavior receives regression coverage through its current command-line surfaces rather than becoming a second new acceptance seam.
- Documentation verification searches the installable skill and public docs for stale claims that successful completion assembles or outputs an image-based PowerPoint file.
- Final verification reviews the changed-file list so unrelated pre-existing workspace changes remain untouched.
- There is little prior automated-test structure in PPTGen, but its existing script-oriented command-line boundaries provide the closest prior art and should be exercised through subprocess-style integration tests.

## Out of Scope

- Automatic invocation or orchestration of the editable-PowerPoint stage.
- How the editable-PowerPoint stage detects chart placement or dimensions.
- How unsupported Data Chart types are represented in editable PowerPoint.
- Any modification to the editable-PowerPoint skill.
- The third skill that opens PowerPoint files in Microsoft PowerPoint and exports PDF for inspection.
- Deterministic local overlay or composition of chart renders into complete slide images.
- Supporting pre-existing image-only charts without structured source data.
- Creating a final editable PowerPoint file within PPTGen.

## Further Notes

- This spec follows the repository glossary terms Project Workspace, Slide Image Set, Data Chart, and Chart Source Package.
- It implements the accepted decisions to use slide images as the skill boundary and Python-generated chart packages as the numerical source of truth.
- A generated full-slide image may contain chart discrepancies because it is produced by a generative backend. That limitation is explicit and does not weaken the accuracy requirements of the independent Chart Source Package.
- The workspace currently contains an unrelated pre-existing deletion in a PPTGen style reference. Implementation must preserve it and avoid including it in this feature's changes.
- PPTGen repository policy requires user-visible documentation changes in Chinese, English, and Korean and an English changelog entry under the unreleased section.
