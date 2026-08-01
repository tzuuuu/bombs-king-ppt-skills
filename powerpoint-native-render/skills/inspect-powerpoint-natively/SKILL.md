---
name: inspect-powerpoint-natively
description: Inspect visible PowerPoint content and appearance through native Microsoft PowerPoint rendering. Use when an agent needs to read or summarize visible slides, analyze presentation style or layout, use a PowerPoint file as a conversion or reconstruction reference, compare presentation visuals, or perform visual QA on a supported presentation, show, or template.
---

# Inspect PowerPoint Natively

Put a native render gate before every judgment about visible PowerPoint content or appearance.

## Check the Runtime

Run the skill-local CLI diagnostic before opening a presentation:

```bash
powerpoint-native-render doctor
```

Continue only when the command returns exit code `0` and JSON with `status: "ok"`. When it returns an error, follow its `repair_action`, report that the native render gate is blocked, and stop the inspection.

Treat a healthy diagnostic only as proof that the local runtime prerequisites are present. Do not treat it as evidence that a presentation was rendered or inspected. If the installed CLI does not expose the later render-and-verify commands required to seal that evidence, report the native render gate as unavailable.
