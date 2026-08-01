# Use slide images as the skill handoff

The image-generation skill hands a complete project workspace to the editable-PowerPoint skill, with the ordered Slide Image Set as the primary content boundary. It does not assemble an intermediate image-based PPTX, because that file adds a lossy and unnecessary container between two workflows that already produce and consume ordered slide images; the workspace retains its outline, specifications, and run state so generation remains traceable and resumable.
