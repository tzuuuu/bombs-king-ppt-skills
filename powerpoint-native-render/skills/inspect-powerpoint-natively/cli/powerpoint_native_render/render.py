from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import importlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional
import uuid
import zipfile


SCHEMA_VERSION = 1
RENDER_CONTRACT_VERSION = 1

MACOS_APPLESCRIPT = r'''
on run argv
    set targetFullName to item 1 of argv
    set destinationPathText to item 2 of argv
    set targetDeck to missing value

    tell application "Microsoft PowerPoint"
        try
            set targetDeck to first presentation whose full name is targetFullName
            save targetDeck in destinationPathText as save as PDF
            set appVersion to Version
            close targetDeck saving no
            set targetDeck to missing value
            return appVersion
        on error errorMessage number errorNumber
            if targetDeck is not missing value then
                try
                    close targetDeck saving no
                end try
            end if
            error errorMessage number errorNumber
        end try
    end tell
end run
'''

MACOS_DISCOVER_APPLESCRIPT = r'''
set previousDelimiters to AppleScript's text item delimiters
set AppleScript's text item delimiters to ASCII character 30
tell application "Microsoft PowerPoint" to set deckNames to full name of every presentation
set joinedNames to deckNames as text
set AppleScript's text item delimiters to previousDelimiters
return joinedNames
'''

MACOS_CLEANUP_APPLESCRIPT = r'''
on run argv
    tell application "Microsoft PowerPoint"
        repeat with targetFullName in argv
            if exists (first presentation whose full name is targetFullName) then
                close (first presentation whose full name is targetFullName) saving no
                return "closed"
            end if
        end repeat
        error "PowerPoint did not expose any exact snapshot cleanup candidate" number 1708
    end tell
end run
'''


class RenderFailure(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        repair_action: str,
        *,
        transient: bool = False,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.repair_action = repair_action
        self.transient = transient

    def as_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "command": "render",
            "status": "error",
            "error_code": self.code,
            "message": self.message,
            "repair_action": self.repair_action,
        }


def _remaining_seconds(deadline: float) -> int:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RenderFailure(
            "POWERPOINT_EXPORT_TIMEOUT",
            "The native render attempt exhausted its timeout budget.",
            "Close blocking dialogs, confirm the source is closed, and retry.",
            transient=True,
        )
    return max(1, math.ceil(remaining))


@dataclass(frozen=True)
class RenderOptions:
    source: Path
    workspace: Path
    settle_seconds: float = 3.0
    timeout: int = 180
    dpi: int = 180


@dataclass(frozen=True)
class ExportResult:
    engine: str
    powerpoint_version: str
    attempts: int = 1


class PowerPointExporter:
    def export(
        self,
        source: Path,
        destination: Path,
        *,
        settle_seconds: float,
        timeout: int,
    ) -> ExportResult:
        raise NotImplementedError


class AutomationRunner:
    def run(
        self,
        script: str,
        arguments: List[str],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        raise NotImplementedError


class SubprocessAutomationRunner(AutomationRunner):
    def __init__(self, command: str) -> None:
        self.command = command

    def run(
        self,
        script: str,
        arguments: List[str],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.command, "-e", script, "--", *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )


class PowerPointLauncher:
    def launch(self, source: Path, *, settle_seconds: float, timeout: int) -> None:
        raise NotImplementedError


class SubprocessPowerPointLauncher(PowerPointLauncher):
    def __init__(self, command: str = "/usr/bin/open") -> None:
        self.command = command

    def launch(self, source: Path, *, settle_seconds: float, timeout: int) -> None:
        try:
            result = subprocess.run(
                [self.command, "-a", "Microsoft PowerPoint", str(source)],
                capture_output=True,
                text=True,
                check=False,
                timeout=min(timeout, 30),
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise RenderFailure(
                "POWERPOINT_OPEN_FAILED",
                f"macOS could not open the exact snapshot in PowerPoint: {error}",
                "Confirm desktop Microsoft PowerPoint is installed and retry.",
                transient=True,
            ) from error
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "open failed").strip()
            raise RenderFailure(
                "POWERPOINT_OPEN_FAILED",
                detail,
                "Confirm desktop Microsoft PowerPoint is installed and retry.",
                transient=True,
            )
        time.sleep(settle_seconds)


class MacPowerPointExporter(PowerPointExporter):
    def __init__(
        self,
        *,
        runner: Optional[AutomationRunner] = None,
        launcher: Optional[PowerPointLauncher] = None,
        osascript: Optional[str] = None,
        staging_root: Optional[Path] = None,
        stability_poll_seconds: float = 0.25,
    ) -> None:
        command = osascript or shutil.which("osascript")
        self.runner = runner or (
            SubprocessAutomationRunner(command) if command is not None else None
        )
        self.launcher = launcher or SubprocessPowerPointLauncher()
        self.staging_root = staging_root or (
            Path.home()
            / "Library"
            / "Containers"
            / "com.microsoft.Powerpoint"
            / "Data"
            / "tmp"
            / "powerpoint-native-render"
        )
        self.stability_poll_seconds = stability_poll_seconds

    def _wait_for_staged_pdf(self, path: Path, *, timeout: int) -> None:
        deadline = time.monotonic() + timeout
        last_size = -1
        stable_reads = 0
        while time.monotonic() < deadline:
            if path.is_file():
                size = path.stat().st_size
                if size > 4 and size == last_size:
                    stable_reads += 1
                else:
                    stable_reads = 0
                last_size = size
                if stable_reads >= 2:
                    with path.open("rb") as staged_file:
                        if staged_file.read(5) == b"%PDF-":
                            return
            time.sleep(self.stability_poll_seconds)
        raise RenderFailure(
            "POWERPOINT_STAGED_PDF_UNSTABLE",
            f"PowerPoint did not finish its staged PDF within {timeout} seconds.",
            "Wait for PowerPoint and PDF writing to finish, then retry.",
            transient=True,
        )

    @staticmethod
    def _remove_staged_export(staging_pdf: Path) -> None:
        if staging_pdf.exists():
            staging_pdf.unlink()
        try:
            staging_pdf.parent.rmdir()
        except OSError:
            pass

    def _cleanup(self, target_full_names: List[str], *, timeout: int) -> None:
        if self.runner is None:
            return
        try:
            cleanup = self.runner.run(
                MACOS_CLEANUP_APPLESCRIPT,
                target_full_names,
                timeout=min(timeout, 15),
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise RenderFailure(
                "POWERPOINT_CLEANUP_FAILED",
                f"Could not close the exact snapshot after export failed: {error}",
                "Close only the read-only snapshot shown in PowerPoint, then retry.",
            ) from error
        if cleanup.returncode != 0:
            detail = (cleanup.stderr or cleanup.stdout or "cleanup failed").strip()
            raise RenderFailure(
                "POWERPOINT_CLEANUP_FAILED",
                f"Could not close the exact snapshot after export failed: {detail}",
                "Close only the read-only snapshot shown in PowerPoint, then retry.",
            )

    @staticmethod
    def _source_path_candidates(source: Path) -> List[str]:
        source_text = str(source)
        candidates = [source_text]
        private_tmp_prefix = "/private/tmp/"
        if source_text.startswith(private_tmp_prefix):
            candidates.append(f"/tmp/{source_text[len(private_tmp_prefix):]}")
        return candidates

    def _discover_target(self, source: Path, *, timeout: int) -> str:
        if self.runner is None:
            raise AssertionError("automation runner is unavailable")
        try:
            discovery = self.runner.run(
                MACOS_DISCOVER_APPLESCRIPT,
                [],
                timeout=min(timeout, 15),
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise RenderFailure(
                "POWERPOINT_TARGET_DISCOVERY_FAILED",
                f"PowerPoint did not report its open presentations: {error}",
                "Close the read-only snapshot shown in PowerPoint, then retry.",
            ) from error
        if discovery.returncode != 0:
            detail = (discovery.stderr or discovery.stdout or "discovery failed").strip()
            raise RenderFailure(
                "POWERPOINT_TARGET_DISCOVERY_FAILED",
                detail,
                "Close the read-only snapshot shown in PowerPoint, then retry.",
            )
        for raw_name in discovery.stdout.split("\x1e"):
            candidate_name = raw_name.strip("\r\n")
            if not candidate_name:
                continue
            candidate = Path(candidate_name)
            try:
                matches = candidate.samefile(source)
            except OSError:
                matches = candidate.resolve() == source.resolve()
            if matches:
                return candidate_name
        raise RenderFailure(
            "POWERPOINT_TARGET_NOT_FOUND",
            "PowerPoint did not report the exact snapshot among its open presentations.",
            "Close any read-only test snapshot shown in PowerPoint, then retry.",
        )

    def export(
        self,
        source: Path,
        destination: Path,
        *,
        settle_seconds: float,
        timeout: int,
    ) -> ExportResult:
        if self.runner is None:
            raise RenderFailure(
                "AUTOMATION_UNAVAILABLE",
                "The macOS osascript command is unavailable.",
                "Restore osascript and run doctor again.",
            )
        deadline = time.monotonic() + timeout
        staging_directory = self.staging_root / uuid.uuid4().hex
        staging_pdf = staging_directory / "powerpoint-export.pdf"
        try:
            staging_directory.mkdir(parents=True, exist_ok=False)
        except OSError as error:
            raise RenderFailure(
                "POWERPOINT_STAGING_UNAVAILABLE",
                f"Cannot create PowerPoint's private PDF staging directory: {error}",
                "Confirm the current user can write to the PowerPoint container, then retry.",
            ) from error
        try:
            self.launcher.launch(
                source,
                settle_seconds=settle_seconds,
                timeout=_remaining_seconds(deadline),
            )
            target_full_name = self._discover_target(
                source,
                timeout=_remaining_seconds(deadline),
            )
        except RenderFailure:
            self._cleanup(
                self._source_path_candidates(source),
                timeout=min(timeout, 15),
            )
            self._remove_staged_export(staging_pdf)
            raise
        try:
            result = self.runner.run(
                MACOS_APPLESCRIPT,
                [
                    target_full_name,
                    str(staging_pdf),
                ],
                timeout=_remaining_seconds(deadline),
            )
        except subprocess.TimeoutExpired as error:
            self._cleanup([target_full_name], timeout=min(timeout, 15))
            self._remove_staged_export(staging_pdf)
            raise RenderFailure(
                "POWERPOINT_EXPORT_TIMEOUT",
                f"PowerPoint export exceeded {timeout} seconds.",
                "Close blocking dialogs, confirm the source is closed, and retry.",
                transient=True,
            ) from error
        except OSError as error:
            self._cleanup([target_full_name], timeout=min(timeout, 15))
            self._remove_staged_export(staging_pdf)
            raise RenderFailure(
                "AUTOMATION_UNAVAILABLE",
                str(error),
                "Restore osascript and run doctor again.",
            ) from error

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "AppleScript failed").strip()
            self._cleanup([target_full_name], timeout=min(timeout, 15))
            self._remove_staged_export(staging_pdf)
            transient_markers = (
                "-600",
                "-609",
                "-1712",
                "isn't running",
                "connection is invalid",
                "timed out",
            )
            is_transient = any(marker.lower() in detail.lower() for marker in transient_markers)
            raise RenderFailure(
                "TRANSIENT_POWERPOINT_AUTOMATION"
                if is_transient
                else "POWERPOINT_EXPORT_FAILED",
                detail,
                "Wait for PowerPoint to finish launching, close blocking dialogs, and retry."
                if is_transient
                else "Open the snapshot manually in PowerPoint, resolve the reported problem, and retry.",
                transient=is_transient,
            )

        try:
            self._wait_for_staged_pdf(
                staging_pdf,
                timeout=_remaining_seconds(deadline),
            )
            shutil.copyfile(staging_pdf, destination)
            if _sha256(staging_pdf) != _sha256(destination):
                raise RenderFailure(
                    "NATIVE_PDF_COPY_MISMATCH",
                    "The retained native PDF differs from PowerPoint's staged export.",
                    "Delete the incomplete run and retry.",
                )
        finally:
            self._remove_staged_export(staging_pdf)

        return ExportResult(
            engine="Microsoft PowerPoint for macOS",
            powerpoint_version=result.stdout.strip() or "unknown",
        )


class PdfRuntime:
    @staticmethod
    def _fitz() -> Any:
        try:
            fitz = importlib.import_module("fitz")
        except ImportError as error:
            raise RenderFailure(
                "MISSING_PDF_RUNTIME",
                "PyMuPDF is required to validate and rasterize the native PDF.",
                "Install the skill CLI with its PyMuPDF dependency, then retry.",
            ) from error
        return fitz

    def wait_until_stable(self, path: Path, *, timeout: int) -> int:
        deadline = time.monotonic() + timeout
        last_size = -1
        stable_reads = 0
        while time.monotonic() < deadline:
            if path.is_file():
                size = path.stat().st_size
                if size > 4 and size == last_size:
                    stable_reads += 1
                else:
                    stable_reads = 0
                last_size = size
                if stable_reads >= 2:
                    try:
                        with self._fitz().open(path) as document:
                            if document.page_count > 0:
                                return int(document.page_count)
                    except RenderFailure:
                        raise
                    except Exception:
                        stable_reads = 0
            time.sleep(0.25)
        raise RenderFailure(
            "PDF_NOT_STABLE",
            f"PowerPoint did not produce a stable, parseable PDF within {timeout} seconds.",
            "Wait for PowerPoint and PDF writing to finish, then retry.",
            transient=True,
        )

    def create_inspection_pdf(self, native_pdf: Path, inspection_pdf: Path) -> int:
        shutil.copyfile(native_pdf, inspection_pdf)
        try:
            with self._fitz().open(inspection_pdf) as document:
                page_count = int(document.page_count)
        except Exception as error:
            raise RenderFailure(
                "INVALID_NATIVE_PDF",
                "The PowerPoint export cannot be parsed as PDF.",
                "Open the snapshot in PowerPoint and confirm it exports successfully.",
            ) from error
        if page_count < 1:
            raise RenderFailure(
                "NO_VISIBLE_SLIDES",
                "The PowerPoint export contains no pages.",
                "Add a visible slide and retry.",
            )
        return page_count

    def rasterize(self, inspection_pdf: Path, pages_dir: Path, *, dpi: int) -> List[Path]:
        pages: List[Path] = []
        try:
            with self._fitz().open(inspection_pdf) as document:
                for page_index, page in enumerate(document):
                    output = pages_dir / f"slide-{page_index + 1}.png"
                    page.get_pixmap(dpi=dpi, alpha=False).save(output)
                    pages.append(output)
        except RenderFailure:
            raise
        except Exception as error:
            raise RenderFailure(
                "PDF_RASTERIZATION_FAILED",
                str(error),
                "Reinstall PyMuPDF and retry the render.",
            ) from error
        return pages


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_options(options: RenderOptions) -> tuple[Path, Path]:
    source = options.source.expanduser().resolve()
    workspace = options.workspace.expanduser().resolve()
    if not 0 <= options.settle_seconds <= 30:
        raise RenderFailure(
            "INVALID_SETTLE_SECONDS",
            "--settle-seconds must be between 0 and 30.",
            "Choose a value from 0 through 30 and retry.",
        )
    if not 30 <= options.timeout <= 900:
        raise RenderFailure(
            "INVALID_TIMEOUT",
            "--timeout must be between 30 and 900 seconds.",
            "Choose a value from 30 through 900 and retry.",
        )
    if not 72 <= options.dpi <= 600:
        raise RenderFailure(
            "INVALID_DPI",
            "--dpi must be between 72 and 600.",
            "Choose a value from 72 through 600 and retry.",
        )
    if not source.is_file():
        raise RenderFailure(
            "SOURCE_NOT_FOUND",
            f"The source does not exist: {source}",
            "Save the presentation and pass its absolute path.",
        )
    if source.suffix.lower() != ".pptx":
        raise RenderFailure(
            "UNSUPPORTED_FORMAT",
            "Ticket 02 supports normal .pptx files only.",
            "Use a .pptx source for this implementation stage.",
        )
    if not zipfile.is_zipfile(source):
        raise RenderFailure(
            "FORMAT_SIGNATURE_MISMATCH",
            "The .pptx source is not an OOXML ZIP package.",
            "Open and resave the file as .pptx in Microsoft PowerPoint.",
        )
    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile) as error:
        raise RenderFailure(
            "DAMAGED_PRESENTATION",
            "The .pptx package could not be read.",
            "Open and repair the presentation manually in Microsoft PowerPoint.",
        ) from error
    if not {"[Content_Types].xml", "ppt/presentation.xml"}.issubset(names):
        raise RenderFailure(
            "FORMAT_SIGNATURE_MISMATCH",
            "The .pptx package is missing required presentation parts.",
            "Open and resave the file as .pptx in Microsoft PowerPoint.",
        )
    workspace.mkdir(parents=True, exist_ok=True)
    return source, workspace


def _artifact(path: Path) -> Dict[str, Any]:
    return {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}


def _render_presentation(
    options: RenderOptions,
    *,
    exporter: Optional[PowerPointExporter] = None,
    pdf_runtime: Optional[PdfRuntime] = None,
) -> Dict[str, Any]:
    source, workspace = _validate_options(options)
    if exporter is None:
        if platform.system() != "Darwin":
            raise RenderFailure(
                "UNSUPPORTED_PLATFORM",
                "Ticket 02 native rendering is available only on macOS.",
                "Run this implementation stage on macOS with desktop PowerPoint.",
            )
        exporter = MacPowerPointExporter()
    pdf = pdf_runtime or PdfRuntime()

    source_hash = _sha256(source)
    run_id = f"{source_hash[:12]}-{uuid.uuid4().hex[:8]}"
    run_directory = workspace / ".powerpoint-render-cache" / "runs" / run_id
    snapshot_directory = run_directory / "snapshot"
    snapshot_directory.mkdir(parents=True, exist_ok=False)
    snapshot = snapshot_directory / f"source{source.suffix.lower()}"
    shutil.copy2(source, snapshot)
    if _sha256(snapshot) != source_hash or _sha256(source) != source_hash:
        raise RenderFailure(
            "SOURCE_MUTATED",
            "The source changed while its immutable snapshot was created.",
            "Save and close the source, then retry.",
        )
    snapshot.chmod(0o444)

    native_pdf = run_directory / "powerpoint-export.pdf"
    inspection_pdf = run_directory / "inspection.pdf"
    pages_directory = run_directory / "pages"
    export_result: Optional[ExportResult] = None
    page_count = 0
    for attempt in (1, 2):
        attempt_deadline = time.monotonic() + options.timeout
        try:
            export_result = exporter.export(
                snapshot.resolve(),
                native_pdf.resolve(),
                settle_seconds=options.settle_seconds,
                timeout=_remaining_seconds(attempt_deadline),
            )
            page_count = pdf.wait_until_stable(
                native_pdf,
                timeout=_remaining_seconds(attempt_deadline),
            )
            export_result = replace(export_result, attempts=attempt)
            break
        except RenderFailure as error:
            if not error.transient or attempt == 2:
                raise
            if native_pdf.exists():
                native_pdf.unlink()
    if export_result is None:
        raise AssertionError("render attempt completed without an export result")

    inspection_page_count = pdf.create_inspection_pdf(native_pdf, inspection_pdf)
    if inspection_page_count != page_count:
        raise RenderFailure(
            "PDF_PAGE_COUNT_MISMATCH",
            "The inspection PDF page count differs from the native export.",
            "Delete the incomplete run and retry.",
        )
    pages_directory.mkdir(parents=True, exist_ok=False)
    pages = pdf.rasterize(inspection_pdf, pages_directory, dpi=options.dpi)
    if len(pages) != page_count:
        raise RenderFailure(
            "PNG_PAGE_COUNT_MISMATCH",
            "The PNG count differs from the inspection PDF page count.",
            "Reinstall PyMuPDF and retry the render.",
        )

    native_artifact = _artifact(native_pdf)
    inspection_artifact = _artifact(inspection_pdf)
    inspection_artifact["derived_from_sha256"] = native_artifact["sha256"]
    page_artifacts: List[Dict[str, Any]] = []
    for page_number, page in enumerate(pages, start=1):
        page_artifact = _artifact(page)
        page_artifact.update(
            {
                "inspection_page_number": page_number,
                "original_slide_number": page_number,
                "derived_from_sha256": inspection_artifact["sha256"],
            }
        )
        page_artifacts.append(page_artifact)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "render_contract_version": RENDER_CONTRACT_VERSION,
        "source": {"path": str(source), "sha256": source_hash},
        "snapshot": _artifact(snapshot),
        "environment": {
            "system": platform.system(),
            "machine": platform.machine(),
            "engine": export_result.engine,
            "powerpoint_version": export_result.powerpoint_version,
        },
        "settings": {
            "settle_seconds": options.settle_seconds,
            "timeout_seconds": options.timeout,
            "dpi": options.dpi,
            "attempts": export_result.attempts,
        },
        "artifacts": {
            "powerpoint_export_pdf": native_artifact,
            "inspection_pdf": inspection_artifact,
            "pages": page_artifacts,
        },
    }
    manifest_path = run_directory / "render.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "command": "render",
        "status": "ok",
        "source": {"path": str(source), "sha256": source_hash},
        "workspace": str(workspace),
        "engine": export_result.engine,
        "powerpoint_version": export_result.powerpoint_version,
        "settings": manifest["settings"],
        "artifacts": {
            "snapshot": str(snapshot.resolve()),
            "powerpoint_export_pdf": str(native_pdf.resolve()),
            "inspection_pdf": str(inspection_pdf.resolve()),
            "pages": [str(page.resolve()) for page in pages],
            "manifest": str(manifest_path.resolve()),
        },
    }


def render_presentation(
    options: RenderOptions,
    *,
    exporter: Optional[PowerPointExporter] = None,
    pdf_runtime: Optional[PdfRuntime] = None,
) -> Dict[str, Any]:
    try:
        return _render_presentation(
            options,
            exporter=exporter,
            pdf_runtime=pdf_runtime,
        )
    except OSError as error:
        raise RenderFailure(
            "FILESYSTEM_OPERATION_FAILED",
            f"A render artifact filesystem operation failed: {error}",
            "Confirm the source and Project Workspace are readable and writable, then retry.",
        ) from error
