"""Load and validate reproducible Data Chart handoff packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class ChartManifestError(ValueError):
    pass


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ChartManifestError(f"Missing chart manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ChartManifestError(f"Invalid JSON in chart_manifest.json: {exc}") from exc
    if not isinstance(payload, dict):
        raise ChartManifestError("chart_manifest.json must contain a JSON object")
    return payload


def _workspace_path(workspace: Path, value: str, label: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        raise ChartManifestError(f"{label} must use a workspace-relative path: {value}")
    resolved = (workspace / raw).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise ChartManifestError(f"{label} escapes the Project Workspace: {value}") from exc
    return resolved


def _has_transparency(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path) as image:
            if image.format != "PNG":
                return False
            if image.mode in {"RGBA", "LA"}:
                return image.getchannel("A").getextrema()[0] < 255
            return "transparency" in image.info
    except (ImportError, OSError):
        return False


def load_chart_manifest(
    workspace: Path,
    slide_ids: set[str],
    *,
    required: bool = False,
) -> tuple[Optional[Path], list[dict[str, Any]]]:
    workspace = Path(workspace).resolve()
    manifest_path = workspace / "chart_manifest.json"
    if not manifest_path.exists():
        if required:
            raise ChartManifestError("Missing chart_manifest.json for planned Data Charts")
        return None, []

    manifest = _read_object(manifest_path)
    if manifest.get("schema_version") != 1:
        raise ChartManifestError("chart_manifest.json must use schema_version 1")
    charts = manifest.get("charts")
    if not isinstance(charts, list):
        raise ChartManifestError("chart_manifest.json charts must be a list")

    seen: set[tuple[str, str]] = set()
    validated: list[dict[str, Any]] = []
    forbidden_fields = {"placement", "coordinates", "dimensions", "bounding_box", "bbox"}
    chart_assets = (workspace / "chart_assets").resolve()
    for index, chart in enumerate(charts, start=1):
        if not isinstance(chart, dict):
            raise ChartManifestError(f"Chart manifest entry {index} must be an object")
        present_forbidden = sorted(forbidden_fields.intersection(chart))
        if present_forbidden:
            raise ChartManifestError(
                f"Chart manifest entry {index} must not define placement: {', '.join(present_forbidden)}"
            )
        for field in ("slide_id", "chart_id", "chart_type", "semantic_purpose", "source_description"):
            if not isinstance(chart.get(field), str) or not chart[field].strip():
                raise ChartManifestError(f"Chart manifest entry {index} has invalid {field}")
        slide_id = chart["slide_id"]
        chart_id = chart["chart_id"]
        identity = (slide_id, chart_id)
        if identity in seen:
            raise ChartManifestError(f"Duplicate chart identity: {slide_id}/{chart_id}")
        seen.add(identity)
        if slide_id not in slide_ids:
            raise ChartManifestError(f"Chart references unknown slide: {slide_id}/{chart_id}")
        if chart.get("required_downstream") is not True:
            raise ChartManifestError(f"Chart must be required downstream: {slide_id}/{chart_id}")
        package = chart.get("package")
        if not isinstance(package, dict):
            raise ChartManifestError(f"Chart package must be an object: {slide_id}/{chart_id}")

        resolved_package: dict[str, str] = {}
        for member in ("script", "data", "image"):
            value = package.get(member)
            if not isinstance(value, str) or not value.strip():
                raise ChartManifestError(f"Chart package is missing {member}: {slide_id}/{chart_id}")
            path = _workspace_path(workspace, value, f"{slide_id}/{chart_id} {member}")
            try:
                path.relative_to(chart_assets)
            except ValueError as exc:
                raise ChartManifestError(
                    f"Chart package member must live in chart_assets: {slide_id}/{chart_id} {member}"
                ) from exc
            if not path.is_file():
                raise ChartManifestError(f"Missing chart package {member}: {slide_id}/{chart_id}")
            resolved_package[member] = str(path)
        if Path(resolved_package["script"]).suffix.lower() != ".py":
            raise ChartManifestError(f"Chart script must be Python: {slide_id}/{chart_id}")
        if Path(resolved_package["data"]).suffix.lower() not in {".csv", ".json"}:
            raise ChartManifestError(f"Chart data snapshot must be CSV or JSON: {slide_id}/{chart_id}")
        if Path(resolved_package["image"]).suffix.lower() != ".png":
            raise ChartManifestError(f"Chart render must be PNG: {slide_id}/{chart_id}")
        if not _has_transparency(Path(resolved_package["image"])):
            raise ChartManifestError(f"Chart render must be a transparent PNG: {slide_id}/{chart_id}")

        normalized = dict(chart)
        normalized["resolved_package"] = resolved_package
        validated.append(normalized)
    return manifest_path.resolve(), validated
