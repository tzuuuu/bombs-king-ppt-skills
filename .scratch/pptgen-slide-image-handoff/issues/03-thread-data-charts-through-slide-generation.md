# 03 — Thread Data Charts through slide generation

**What to build:** Make a Data Chart planned in an approved deck flow end to end into a Chart Source Package, chart manifest entry, self-contained slide job, and recorded full-slide image. The image backend receives the accurate rendered chart as required visual context and still generates the complete slide layout; workers cannot modify chart packages, reserve chart placeholders, or construct final slides locally.

**Blocked by:** 02 — Validate reproducible Chart Source Packages.

**Status:** ready-for-agent

- [ ] An approved deck can declare one or more planned Data Charts and associate each one with a slide and semantic purpose.
- [ ] Preparing slide jobs fails when a planned Data Chart lacks a complete Chart Source Package or manifest entry.
- [ ] Every relevant slide job includes the rendered chart as a required input with an explicit Data Chart role, not as loose style inspiration.
- [ ] Chart package metadata remains workspace-relative and is carried consistently from deck planning into generated jobs and run state.
- [ ] Slide-worker instructions prohibit changing the Chart Source Package, generating replacement chart values, reserving a placeholder, and using deterministic local composition.
- [ ] The image backend remains the only producer of the complete final slide image.
- [ ] Recording a slide result preserves existing backend provenance and state-transition guarantees.
- [ ] A representative chart-bearing slide can proceed from approved deck input through job preparation and result recording, then pass Project Workspace handoff validation.
- [ ] Regression coverage confirms slides without Data Charts continue to use the existing job preparation and recording behaviour.
