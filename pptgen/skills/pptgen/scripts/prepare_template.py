#!/usr/bin/env python3
"""Copy and render a user-supplied PowerPoint master template.

The command creates one deterministic template package inside a pptgen
Project Workspace:

    template/template.pptx or template/template.ppt
    template/template.pdf
    template/template-1.png, template/template-2.png, ...
    template/template_manifest.json

Native PowerPoint is used for PPT/PPTX-to-PDF conversion so master backgrounds,
fonts, shadows, and native layout are rendered by the same application that
users normally use to open the template. Poppler's ``pdftoppm`` renders the
PDF pages into PNGs for image-generation context.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


SUPPORTED_SUFFIXES = {".ppt", ".pptx"}
DEFAULT_TIMEOUT = 180
DEFAULT_DPI = 180


class TemplateError(RuntimeError):
    """Raised when the template package cannot be prepared."""


MACOS_APPLESCRIPT = r'''
on run argv
    set sourcePathText to item 1 of argv
    set destinationPathText to item 2 of argv
    set settleSeconds to (item 3 of argv) as real
    set sourceFile to POSIX file sourcePathText
    set destinationFile to POSIX file destinationPathText

    tell application "Microsoft PowerPoint"
        open sourceFile
        delay settleSeconds
        set targetDeck to last presentation
        activate

        try
            save targetDeck in destinationFile as save as PDF
        on error errorMessage number errorNumber
            try
                close targetDeck saving no
            end try
            error errorMessage number errorNumber
        end try

        close targetDeck saving no
    end tell
end run
'''


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        help="User-supplied PowerPoint master template (.ppt or .pptx).",
    )
    parser.add_argument(
        "workspace",
        type=Path,
        help="pptgen Project Workspace that will receive the template package.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing template package in the workspace.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"PowerPoint/PDF command timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=3.0,
        help="Wait after opening the template so fonts and layout can settle (default: 3).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"PNG render resolution (default: {DEFAULT_DPI}).",
    )
    return parser.parse_args()


def _run_checked(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise TemplateError(f"Required command was not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise TemplateError(f"Command timed out after {timeout}s: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        raise TemplateError(f"Command failed: {details}") from exc


def _resolve_source(source: Path) -> Path:
    resolved = source.expanduser().resolve()
    if not resolved.is_file():
        raise TemplateError(f"Template source does not exist: {resolved}")
    if resolved.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise TemplateError("Template source must be a .ppt or .pptx file: " f"{resolved}")
    return resolved


def _prepare_destination(
    source: Path,
    workspace: Path,
    *,
    overwrite: bool,
) -> tuple[Path, Path, Path]:
    workspace = workspace.expanduser().resolve()
    template_dir = workspace / "template"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_source = template_dir / f"template{source.suffix.lower()}"
    pdf_path = template_dir / "template.pdf"
    manifest_path = template_dir / "template_manifest.json"
    existing = [
        template_dir / "template.ppt",
        template_dir / "template.pptx",
        pdf_path,
        manifest_path,
        *sorted(template_dir.glob("template-*.png")),
    ]
    existing = [path for path in existing if path.exists()]
    if existing and not overwrite:
        names = ", ".join(path.name for path in existing)
        raise TemplateError(
            f"Template package already exists ({names}); pass --overwrite to replace it."
        )
    if overwrite:
        for path in existing:
            if path.resolve() != source.resolve():
                path.unlink()
    if template_source.resolve() != source.resolve():
        shutil.copy2(source, template_source)
    return template_source, pdf_path, manifest_path


def _export_on_macos(
    source: Path,
    output: Path,
    *,
    timeout: int,
    settle_seconds: float,
) -> str:
    powerpoint = Path("/Applications/Microsoft PowerPoint.app")
    if not powerpoint.exists():
        raise TemplateError("Microsoft PowerPoint is not installed in /Applications")
    if shutil.which("osascript") is None:
        raise TemplateError("macOS osascript command is unavailable")
    _run_checked(
        [
            "osascript",
            "-e",
            MACOS_APPLESCRIPT,
            str(source),
            str(output),
            str(settle_seconds),
        ],
        timeout=timeout,
    )
    return "Microsoft PowerPoint for macOS"


def _export_on_windows(
    source: Path,
    output: Path,
    *,
    settle_seconds: float,
) -> str:
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError as exc:
        raise TemplateError("Windows template export requires pywin32: pip install pywin32") from exc

    powerpoint = None
    presentation = None
    try:
        powerpoint = win32com.client.DispatchEx("PowerPoint.Application")
        powerpoint.Visible = True
        presentation = powerpoint.Presentations.Open(
            str(source), ReadOnly=True, Untitled=False, WithWindow=False
        )
        time.sleep(settle_seconds)
        presentation.SaveAs(str(output), 32)
    except Exception as exc:
        raise TemplateError(f"PowerPoint automation failed: {exc}") from exc
    finally:
        if presentation is not None:
            presentation.Close()
        if powerpoint is not None:
            powerpoint.Quit()
    return "Microsoft PowerPoint for Windows"


def _wait_for_pdf(output: Path, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last_size = -1
    stable_checks = 0
    while time.monotonic() < deadline:
        if output.exists():
            size = output.stat().st_size
            if size > 4 and size == last_size:
                stable_checks += 1
            else:
                stable_checks = 0
            last_size = size
            if stable_checks >= 2:
                break
        time.sleep(0.25)
    else:
        raise TemplateError(f"PowerPoint did not finish writing the PDF: {output}")
    with output.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise TemplateError(f"Output is not a valid PDF file: {output}")


def _render_pdf(
    pdf_path: Path,
    template_dir: Path,
    *,
    dpi: int,
    timeout: int,
) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise TemplateError("Template PNG rendering requires Poppler's pdftoppm command")
    if dpi < 72 or dpi > 600:
        raise TemplateError("--dpi must be between 72 and 600")
    prefix = template_dir / "template"
    _run_checked(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        timeout=timeout,
    )
    images = sorted(
        (path for path in template_dir.glob("template-*.png") if path.is_file()),
        key=_template_page_number,
    )
    if not images:
        raise TemplateError(f"PDF render produced no template page images: {pdf_path}")
    return images


def _template_page_number(path: Path) -> int:
    try:
        return int(path.stem.rsplit("-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise TemplateError(f"Unexpected template render filename: {path.name}") from exc


def _write_manifest(
    manifest_path: Path,
    *,
    workspace: Path,
    template_source: Path,
    pdf_path: Path,
    images: list[Path],
    dpi: int,
    renderer: str,
) -> None:
    def relative(path: Path) -> str:
        return path.resolve().relative_to(workspace.resolve()).as_posix()

    payload = {
        "schema_version": 1,
        "source": relative(template_source),
        "pdf": relative(pdf_path),
        "rendered_pages": [relative(path) for path in images],
        "page_count": len(images),
        "dpi": dpi,
        "renderer": renderer,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_template(
    source: Path,
    workspace: Path,
    *,
    overwrite: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    settle_seconds: float = 3.0,
    dpi: int = DEFAULT_DPI,
) -> dict[str, object]:
    if timeout < 1:
        raise TemplateError("--timeout must be at least 1 second")
    if settle_seconds < 0 or settle_seconds > 30:
        raise TemplateError("--settle-seconds must be between 0 and 30")
    source = _resolve_source(source)
    workspace = workspace.expanduser().resolve()
    template_source, pdf_path, manifest_path = _prepare_destination(
        source,
        workspace,
        overwrite=overwrite,
    )
    system = platform.system()
    if system == "Darwin":
        renderer = _export_on_macos(
            template_source,
            pdf_path,
            timeout=timeout,
            settle_seconds=settle_seconds,
        )
    elif system == "Windows":
        renderer = _export_on_windows(
            template_source,
            pdf_path,
            settle_seconds=settle_seconds,
        )
    else:
        raise TemplateError(
            "Native PowerPoint template rendering is supported only on macOS or Windows."
        )
    _wait_for_pdf(pdf_path, timeout)
    images = _render_pdf(pdf_path, template_source.parent, dpi=dpi, timeout=timeout)
    _write_manifest(
        manifest_path,
        workspace=workspace,
        template_source=template_source,
        pdf_path=pdf_path,
        images=images,
        dpi=dpi,
        renderer=renderer,
    )
    return {
        "status": "ok",
        "source": str(template_source),
        "pdf": str(pdf_path),
        "rendered_pages": [str(path) for path in images],
        "page_count": len(images),
        "manifest": str(manifest_path),
        "renderer": renderer,
    }


def main() -> int:
    args = _parse_args()
    try:
        result = prepare_template(
            args.source,
            args.workspace,
            overwrite=args.overwrite,
            timeout=args.timeout,
            settle_seconds=args.settle_seconds,
            dpi=args.dpi,
        )
    except TemplateError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
