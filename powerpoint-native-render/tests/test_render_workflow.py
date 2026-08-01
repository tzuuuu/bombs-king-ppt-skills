from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CLI_ROOT = PACKAGE_ROOT / "skills" / "inspect-powerpoint-natively" / "cli"
sys.path.insert(0, str(CLI_ROOT))

from powerpoint_native_render.render import (  # noqa: E402
    ExportResult,
    MACOS_DISCOVER_APPLESCRIPT,
    MACOS_APPLESCRIPT,
    MACOS_CLEANUP_APPLESCRIPT,
    AutomationRunner,
    MacPowerPointExporter,
    PowerPointLauncher,
    PdfRuntime,
    PowerPointExporter,
    RenderFailure,
    RenderOptions,
    render_presentation,
)


def make_minimal_pptx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("ppt/presentation.xml", "<p:presentation />")


class RecordingExporter(PowerPointExporter):
    def __init__(self) -> None:
        self.sources: list[Path] = []
        self.destinations: list[Path] = []
        self.settle_seconds: list[float] = []
        self.timeouts: list[int] = []

    def export(
        self,
        source: Path,
        destination: Path,
        *,
        settle_seconds: float,
        timeout: int,
    ) -> ExportResult:
        self.sources.append(source)
        self.destinations.append(destination)
        self.settle_seconds.append(settle_seconds)
        self.timeouts.append(timeout)
        destination.write_bytes(b"native-pdf")
        return ExportResult(
            engine="Microsoft PowerPoint for macOS",
            powerpoint_version="16.test",
            attempts=1,
        )


class RecordingPdfRuntime(PdfRuntime):
    def wait_until_stable(self, path: Path, *, timeout: int) -> int:
        self.assert_native(path)
        return 1

    def create_inspection_pdf(self, native_pdf: Path, inspection_pdf: Path) -> int:
        self.assert_native(native_pdf)
        inspection_pdf.write_bytes(native_pdf.read_bytes())
        return 1

    def rasterize(self, inspection_pdf: Path, pages_dir: Path, *, dpi: int) -> list[Path]:
        self.assert_native(inspection_pdf)
        page = pages_dir / "slide-1.png"
        page.write_bytes(f"png-at-{dpi}-dpi".encode("ascii"))
        return [page]

    @staticmethod
    def assert_native(path: Path) -> None:
        if path.read_bytes() != b"native-pdf":
            raise AssertionError("native PDF changed before derivation")


class FlakyExporter(RecordingExporter):
    def export(
        self,
        source: Path,
        destination: Path,
        *,
        settle_seconds: float,
        timeout: int,
    ) -> ExportResult:
        if not self.sources:
            self.sources.append(source)
            self.destinations.append(destination)
            self.settle_seconds.append(settle_seconds)
            self.timeouts.append(timeout)
            destination.write_bytes(b"partial")
            raise RenderFailure(
                "TRANSIENT_POWERPOINT_AUTOMATION",
                "PowerPoint is still launching.",
                "Wait and retry.",
                transient=True,
            )
        return super().export(
            source,
            destination,
            settle_seconds=settle_seconds,
            timeout=timeout,
        )


class RecordingLauncher(PowerPointLauncher):
    def __init__(self) -> None:
        self.calls: list[tuple[Path, float, int]] = []

    def launch(self, source: Path, *, settle_seconds: float, timeout: int) -> None:
        self.calls.append((source, settle_seconds, timeout))


class TimeoutThenCleanupRunner(AutomationRunner):
    def __init__(self, source: Path) -> None:
        self.scripts: list[str] = []
        self.source = source

    def run(
        self, script: str, arguments: list[str], *, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        self.scripts.append(script)
        if script == MACOS_DISCOVER_APPLESCRIPT:
            return subprocess.CompletedProcess(
                ["osascript"], 0, f"{self.source}\x1e", ""
            )
        if script == MACOS_APPLESCRIPT:
            raise subprocess.TimeoutExpired("osascript", timeout)
        return subprocess.CompletedProcess(["osascript"], 0, "", "")


class SuccessfulStagedExportRunner(AutomationRunner):
    def __init__(self, source: Path) -> None:
        self.source = source
        self.export_destination: Path | None = None

    def run(
        self, script: str, arguments: list[str], *, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        if script == MACOS_DISCOVER_APPLESCRIPT:
            return subprocess.CompletedProcess(
                ["osascript"], 0, f"{self.source}\x1e", ""
            )
        if script == MACOS_APPLESCRIPT:
            self.export_destination = Path(arguments[1])
            self.export_destination.write_bytes(b"%PDF-native")
            return subprocess.CompletedProcess(["osascript"], 0, "16.test\n", "")
        raise AssertionError("cleanup should not run after a successful export")


class RenderWorkflowTests(unittest.TestCase):
    def test_macos_export_stages_inside_powerpoint_container_then_copies_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.pptx"
            source.write_bytes(b"source")
            destination = root / "artifacts" / "powerpoint-export.pdf"
            destination.parent.mkdir()
            staging_root = root / "powerpoint-container"
            runner = SuccessfulStagedExportRunner(source)
            launcher = RecordingLauncher()
            exporter = MacPowerPointExporter(
                runner=runner,
                launcher=launcher,
                osascript="/usr/bin/osascript",
                staging_root=staging_root,
                stability_poll_seconds=0,
            )

            result = exporter.export(
                source,
                destination,
                settle_seconds=3,
                timeout=30,
            )

            self.assertEqual(result.powerpoint_version, "16.test")
            self.assertEqual(destination.read_bytes(), b"%PDF-native")
            self.assertIsNotNone(runner.export_destination)
            self.assertTrue(str(runner.export_destination).startswith(str(staging_root)))
            self.assertFalse(runner.export_destination.exists())

    def test_macos_timeout_closes_the_exact_snapshot_before_retrying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path("/private/tmp/run/snapshot/source.pptx")
            runner = TimeoutThenCleanupRunner(source)
            launcher = RecordingLauncher()
            exporter = MacPowerPointExporter(
                runner=runner,
                launcher=launcher,
                osascript="/usr/bin/osascript",
                staging_root=Path(temporary_directory) / "staging",
            )

            with self.assertRaises(RenderFailure) as caught:
                exporter.export(
                    source,
                    Path("/private/tmp/run/powerpoint-export.pdf"),
                    settle_seconds=3,
                    timeout=30,
                )

            self.assertTrue(caught.exception.transient)
            self.assertEqual(
                runner.scripts,
                [
                    MACOS_DISCOVER_APPLESCRIPT,
                    MACOS_APPLESCRIPT,
                    MACOS_CLEANUP_APPLESCRIPT,
                ],
            )
            self.assertEqual(launcher.calls, [(source, 3, 30)])
            self.assertNotIn("open source", MACOS_APPLESCRIPT)
            self.assertNotIn("last presentation", MACOS_APPLESCRIPT)
            self.assertIn(
                "output type of print options of targetDeck to print slides",
                MACOS_APPLESCRIPT,
            )
            self.assertNotIn("print notes pages", MACOS_APPLESCRIPT)

    def test_render_cli_reports_a_structured_error_on_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(CLI_ROOT)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "powerpoint_native_render.cli",
                    "render",
                    str(root / "missing.pptx"),
                    "--workspace",
                    str(root / "workspace"),
                    "--settle-seconds",
                    "5",
                    "--timeout",
                    "90",
                    "--dpi",
                    "240",
                ],
                cwd=PACKAGE_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["command"], "render")
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["error_code"], "SOURCE_NOT_FOUND")
            self.assertEqual(result.stdout.count("\n"), 1)
            self.assertEqual(result.stderr, "")

    def test_render_uses_exact_snapshot_and_reports_traceable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source deck.pptx"
            workspace = root / "workspace"
            make_minimal_pptx(source)
            original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            exporter = RecordingExporter()

            payload = render_presentation(
                RenderOptions(
                    source=source,
                    workspace=workspace,
                    settle_seconds=4.5,
                    timeout=75,
                    dpi=220,
                ),
                exporter=exporter,
                pdf_runtime=RecordingPdfRuntime(),
            )

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["command"], "render")
            self.assertEqual(payload["source"]["sha256"], original_hash)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)
            self.assertEqual(len(exporter.sources), 1)
            snapshot = exporter.sources[0]
            self.assertTrue(snapshot.is_absolute())
            self.assertNotEqual(snapshot, source.resolve())
            self.assertTrue(snapshot.is_relative_to(workspace.resolve()))
            self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), original_hash)
            self.assertEqual(exporter.settle_seconds, [4.5])
            self.assertEqual(exporter.timeouts, [75])

            artifacts = payload["artifacts"]
            for key in ("snapshot", "powerpoint_export_pdf", "inspection_pdf", "manifest"):
                self.assertTrue(Path(artifacts[key]).is_absolute())
                self.assertTrue(Path(artifacts[key]).is_file())
            self.assertEqual(len(artifacts["pages"]), 1)
            self.assertEqual(Path(artifacts["pages"][0]).name, "slide-1.png")
            self.assertEqual(Path(artifacts["powerpoint_export_pdf"]).read_bytes(), b"native-pdf")

            manifest = json.loads(Path(artifacts["manifest"]).read_text(encoding="utf-8"))
            native_hash = manifest["artifacts"]["powerpoint_export_pdf"]["sha256"]
            self.assertEqual(
                manifest["artifacts"]["inspection_pdf"]["derived_from_sha256"],
                native_hash,
            )
            self.assertEqual(
                manifest["artifacts"]["pages"][0]["original_slide_number"], 1
            )
            self.assertEqual(
                manifest["artifacts"]["pages"][0]["derived_from_sha256"],
                manifest["artifacts"]["inspection_pdf"]["sha256"],
            )
            self.assertEqual(manifest["settings"]["dpi"], 220)
            self.assertEqual(manifest["settings"]["settle_seconds"], 4.5)
            self.assertEqual(manifest["settings"]["timeout_seconds"], 75)

    def test_render_retries_one_transient_failure_and_reuses_the_exact_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "fixture.pptx"
            make_minimal_pptx(source)
            exporter = FlakyExporter()

            payload = render_presentation(
                RenderOptions(source=source, workspace=root / "workspace"),
                exporter=exporter,
                pdf_runtime=RecordingPdfRuntime(),
            )

            self.assertEqual(len(exporter.sources), 2)
            self.assertEqual(exporter.sources[0], exporter.sources[1])
            self.assertEqual(payload["settings"]["attempts"], 2)

    def test_render_rejects_invalid_external_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "fixture.pptx"
            make_minimal_pptx(source)

            for field, value, code in (
                ("settle_seconds", -0.1, "INVALID_SETTLE_SECONDS"),
                ("settle_seconds", 30.1, "INVALID_SETTLE_SECONDS"),
                ("timeout", 29, "INVALID_TIMEOUT"),
                ("timeout", 901, "INVALID_TIMEOUT"),
                ("dpi", 71, "INVALID_DPI"),
                ("dpi", 601, "INVALID_DPI"),
            ):
                values = {
                    "source": source,
                    "workspace": root / "workspace",
                    "settle_seconds": 3.0,
                    "timeout": 180,
                    "dpi": 180,
                }
                values[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(Exception, code):
                        render_presentation(
                            RenderOptions(**values),
                            exporter=RecordingExporter(),
                            pdf_runtime=RecordingPdfRuntime(),
                        )


if __name__ == "__main__":
    unittest.main()
