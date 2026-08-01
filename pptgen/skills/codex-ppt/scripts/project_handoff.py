#!/usr/bin/env python3
"""Initialize and validate a codex-ppt Project Workspace handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Optional

from chart_manifest import ChartManifestError, load_chart_manifest


class HandoffError(ValueError):
    """A Project Workspace is not ready for handoff."""


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _init_workspace(target: str) -> int:
    workspace = Path(target).expanduser().resolve()
    for name in ("origin_image", "prompts", "chart_assets"):
        (workspace / name).mkdir(parents=True, exist_ok=True)
    _print_json({"status": "initialized", "project_workspace": str(workspace)})
    return 0


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HandoffError(f"Missing required artifact: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise HandoffError(f"Invalid JSON in {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HandoffError(f"Expected a JSON object in {path.name}")
    return payload


def _require_inside(workspace: Path, value: str, label: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        raise HandoffError(f"{label} must use a workspace-relative path: {value}")
    resolved = (workspace / raw).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise HandoffError(f"{label} escapes the Project Workspace: {value}") from exc
    return resolved


def _validate_workspace(target: str) -> int:
    workspace = Path(target).expanduser().resolve()
    if not workspace.is_dir():
        raise HandoffError(f"Project Workspace does not exist: {workspace}")

    for directory in ("origin_image", "prompts", "chart_assets"):
        if not (workspace / directory).is_dir():
            raise HandoffError(f"Missing required workspace directory: {directory}")
    for artifact in ("outline.md", "deck_spec.json"):
        if not (workspace / artifact).is_file():
            raise HandoffError(f"Missing required artifact: {artifact}")
    if list(workspace.glob("*.pptx")):
        raise HandoffError("Project Workspace must not contain an intermediate PPTX")

    deck_spec = _read_json(workspace / "deck_spec.json")
    jobs = _read_json(workspace / "slide_jobs.json")
    run_state = _read_json(workspace / "slide_run_state.json")
    slides = jobs.get("slides")
    if not isinstance(slides, list) or not slides:
        raise HandoffError("slide_jobs.json must contain at least one slide")

    expected_images: set[Path] = set()
    slide_ids: set[str] = set()
    for slide in slides:
        if not isinstance(slide, dict):
            raise HandoffError("Every slide job must be a JSON object")
        slide_id = str(slide.get("slide_id") or "unknown slide")
        if slide_id in slide_ids:
            raise HandoffError(f"Duplicate slide identity: {slide_id}")
        slide_ids.add(slide_id)
        status = slide.get("status")
        if status not in {"accepted", "recorded"}:
            raise HandoffError(f"{slide_id} is not ready for handoff: {status}")
        out = slide.get("out") or f"origin_image/{slide_id}.png"
        if not isinstance(out, str):
            raise HandoffError(f"{slide_id} has an invalid output path")
        image_path = _require_inside(workspace, out, f"{slide_id} output")
        if image_path.parent != (workspace / "origin_image").resolve():
            raise HandoffError(f"{slide_id} output must be in the Slide Image Set")
        if not image_path.is_file():
            raise HandoffError(f"Missing expected slide image: {image_path.name}")
        expected_images.add(image_path)

    actual_images = {
        path.resolve()
        for path in (workspace / "origin_image").iterdir()
        if path.is_file() and path.name.lower().startswith("slide_") and path.suffix.lower() == ".png"
    }
    unexpected = sorted(path.name for path in actual_images - expected_images)
    if unexpected:
        raise HandoffError(f"Unexpected slide images: {', '.join(unexpected)}")
    if jobs.get("run_status") != "slides_recorded":
        raise HandoffError(f"Slide jobs are not complete: {jobs.get('run_status')}")
    if run_state.get("status") != "slides_recorded":
        raise HandoffError(f"Slide run state is not complete: {run_state.get('status')}")

    planned_charts: set[tuple[str, str]] = set()
    spec_slides = deck_spec.get("slides", [])
    if spec_slides is not None and not isinstance(spec_slides, list):
        raise HandoffError("deck_spec.json slides must be a list")
    for fallback, slide in enumerate(spec_slides or [], start=1):
        if not isinstance(slide, dict):
            raise HandoffError(f"Deck spec slide {fallback} must be an object")
        number = slide.get("number", fallback)
        try:
            slide_id = f"slide_{int(number):02d}"
        except (TypeError, ValueError) as exc:
            raise HandoffError(f"Invalid deck spec slide number: {number}") from exc
        entries = slide.get("data_charts") or []
        if not isinstance(entries, list):
            entries = [entries]
        for entry in entries:
            chart_id = entry.get("chart_id") if isinstance(entry, dict) else entry
            if not isinstance(chart_id, str) or not chart_id.strip():
                raise HandoffError(f"{slide_id} has an invalid planned Data Chart")
            planned_charts.add((slide_id, chart_id.strip()))

    try:
        chart_manifest, charts = load_chart_manifest(
            workspace,
            slide_ids,
            required=bool(planned_charts),
        )
    except ChartManifestError as exc:
        raise HandoffError(str(exc)) from exc
    delivered_charts = {(chart["slide_id"], chart["chart_id"]) for chart in charts}
    missing_charts = sorted(planned_charts - delivered_charts)
    if missing_charts:
        raise HandoffError(
            "Planned Data Charts are missing Chart Source Packages: "
            + ", ".join(f"{slide_id}/{chart_id}" for slide_id, chart_id in missing_charts)
        )
    unplanned_charts = sorted(delivered_charts - planned_charts)
    if unplanned_charts:
        raise HandoffError(
            "Chart manifest contains unplanned Data Charts: "
            + ", ".join(f"{slide_id}/{chart_id}" for slide_id, chart_id in unplanned_charts)
        )

    _print_json(
        {
            "status": "ready_for_handoff",
            "project_workspace": str(workspace),
            "slide_image_set": str((workspace / "origin_image").resolve()),
            "slide_count": len(slides),
            "selected_backend": jobs.get("selected_backend"),
            "recorded_result_status": jobs.get("run_status"),
            "outline": str((workspace / "outline.md").resolve()),
            "outline_present": True,
            "speaker_script": str((workspace / "speech.md").resolve())
            if (workspace / "speech.md").is_file()
            else None,
            "speaker_script_present": (workspace / "speech.md").is_file(),
            "slide_jobs": str((workspace / "slide_jobs.json").resolve()),
            "chart_manifest": str(chart_manifest) if chart_manifest else None,
            "chart_count": len(charts),
        }
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="Initialize a Project Workspace.")
    init_parser.add_argument("workspace")
    validate_parser = subparsers.add_parser("validate", help="Validate a Project Workspace handoff.")
    validate_parser.add_argument("workspace")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "init":
            return _init_workspace(args.workspace)
        if args.command == "validate":
            return _validate_workspace(args.workspace)
        raise AssertionError(f"Unhandled command: {args.command}")
    except HandoffError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
