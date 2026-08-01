from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SKILL_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_SCRIPT = SKILL_ROOT / "scripts" / "project_handoff.py"
PREPARE_SCRIPT = SKILL_ROOT / "scripts" / "prepare_slide_prompts.py"
DISPATCH_SCRIPT = SKILL_ROOT / "scripts" / "record_slide_dispatch.py"
RECORD_SCRIPT = SKILL_ROOT / "scripts" / "record_slide_result.py"


class ProjectHandoffCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HANDOFF_SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def assert_invalid(self, workspace: Path, message: str) -> None:
        result = self.run_cli("validate", str(workspace))
        self.assertNotEqual(result.returncode, 0)
        error = json.loads(result.stderr)
        self.assertEqual(error["status"], "invalid")
        self.assertIn(message, error["error"])

    def test_init_creates_project_workspace_without_pptx(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "quarterly-report"

            result = self.run_cli("init", str(workspace))

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "initialized")
            self.assertEqual(Path(summary["project_workspace"]), workspace.resolve())
            self.assertTrue((workspace / "origin_image").is_dir())
            self.assertTrue((workspace / "generated_images").is_dir())
            self.assertTrue((workspace / "prompts").is_dir())
            self.assertTrue((workspace / "chart_assets").is_dir())
            self.assertEqual(list(workspace.glob("*.pptx")), [])

    def create_slide_only_workspace(self, root: Path) -> Path:
        workspace = root / "quarterly-report"
        for name in ("origin_image", "generated_images", "prompts", "chart_assets"):
            (workspace / name).mkdir(parents=True, exist_ok=True)
        (workspace / "outline.md").write_text("# Approved outline\n", encoding="utf-8")
        (workspace / "deck_spec.json").write_text(
            json.dumps({"slides": [{"number": 1}, {"number": 2}]}) + "\n",
            encoding="utf-8",
        )
        (workspace / "slide_run_state.json").write_text(
            json.dumps({"status": "slides_recorded"}) + "\n", encoding="utf-8"
        )
        jobs = {
            "selected_backend": "built-in image tool",
            "sample_generation_method": {"backend_used": "built-in image tool"},
            "run_status": "slides_recorded",
            "slides": [
                {
                    "slide_id": "slide_01",
                    "status": "accepted",
                    "out": "origin_image/slide_01.png",
                },
                {
                    "slide_id": "slide_02",
                    "status": "recorded",
                    "out": "origin_image/slide_02.png",
                },
            ],
        }
        (workspace / "slide_jobs.json").write_text(
            json.dumps(jobs) + "\n", encoding="utf-8"
        )
        (workspace / "origin_image" / "slide_01.png").write_bytes(b"slide one")
        (workspace / "origin_image" / "slide_02.png").write_bytes(b"slide two")
        return workspace

    def test_validate_accepts_complete_slide_only_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))

            result = self.run_cli("validate", str(workspace))

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "ready_for_handoff")
            self.assertEqual(summary["slide_count"], 2)
            self.assertEqual(summary["slide_image_set"], str((workspace / "origin_image").resolve()))
            self.assertEqual(summary["generated_images"], str((workspace / "generated_images").resolve()))
            self.assertEqual(summary["selected_backend"], "built-in image tool")
            self.assertEqual(summary["recorded_result_status"], "slides_recorded")
            self.assertTrue(summary["outline_present"])
            self.assertFalse(summary["speaker_script_present"])
            self.assertEqual(summary["regenerated_slides"], [])
            self.assertEqual(summary["blocked_slides"], [])
            self.assertEqual(len(summary["known_limitations"]), 2)

    def add_chart_package(
        self,
        workspace: Path,
        *,
        slide_id: str = "slide_02",
        chart_id: str = "chart_01",
    ) -> None:
        package = workspace / "chart_assets" / slide_id / chart_id
        package.mkdir(parents=True, exist_ok=True)
        (package / "chart.py").write_text(
            "from pathlib import Path\nPath(__file__).with_name('chart.png').write_bytes(b'png')\n",
            encoding="utf-8",
        )
        (package / "data.csv").write_text("month,value\nJan,10\nFeb,12\n", encoding="utf-8")
        image = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
        image.putpixel((0, 0), (31, 119, 180, 255))
        image.save(package / "chart.png")
        manifest = {
            "schema_version": 1,
            "charts": [
                {
                    "slide_id": slide_id,
                    "chart_id": chart_id,
                    "chart_type": "line",
                    "semantic_purpose": "Show monthly growth",
                    "source_description": "Approved report data",
                    "required_downstream": True,
                    "package": {
                        "script": f"chart_assets/{slide_id}/{chart_id}/chart.py",
                        "data": f"chart_assets/{slide_id}/{chart_id}/data.csv",
                        "image": f"chart_assets/{slide_id}/{chart_id}/chart.png",
                    },
                }
            ],
        }
        (workspace / "chart_manifest.json").write_text(
            json.dumps(manifest) + "\n", encoding="utf-8"
        )
        number = int(slide_id.removeprefix("slide_"))
        deck_spec = json.loads((workspace / "deck_spec.json").read_text(encoding="utf-8"))
        for slide in deck_spec["slides"]:
            if slide["number"] == number:
                slide["data_charts"] = [chart_id]
                break
        (workspace / "deck_spec.json").write_text(
            json.dumps(deck_spec) + "\n", encoding="utf-8"
        )

    def test_validate_accepts_reproducible_chart_source_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            self.add_chart_package(workspace)

            result = self.run_cli("validate", str(workspace))

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["chart_count"], 1)
            self.assertEqual(
                summary["chart_manifest"], str((workspace / "chart_manifest.json").resolve())
            )

    def test_validate_rejects_missing_slide_and_incomplete_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            (workspace / "origin_image" / "slide_02.png").unlink()
            self.assert_invalid(workspace, "Missing expected slide image")

            (workspace / "origin_image" / "slide_02.png").write_bytes(b"slide two")
            jobs = json.loads((workspace / "slide_jobs.json").read_text(encoding="utf-8"))
            jobs["slides"][1]["status"] = "pending"
            (workspace / "slide_jobs.json").write_text(json.dumps(jobs) + "\n", encoding="utf-8")
            self.assert_invalid(workspace, "slide_02 is not ready for handoff")

    def test_validate_rejects_jobs_or_names_that_do_not_match_deck_spec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            jobs = json.loads((workspace / "slide_jobs.json").read_text(encoding="utf-8"))
            jobs["slides"].pop()
            (workspace / "slide_jobs.json").write_text(json.dumps(jobs) + "\n", encoding="utf-8")
            self.assert_invalid(workspace, "missing jobs: slide_02")

            workspace = self.create_slide_only_workspace(Path(temp_dir) / "second")
            jobs = json.loads((workspace / "slide_jobs.json").read_text(encoding="utf-8"))
            jobs["slides"][0]["out"] = "origin_image/cover.png"
            (workspace / "slide_jobs.json").write_text(json.dumps(jobs) + "\n", encoding="utf-8")
            (workspace / "origin_image" / "cover.png").write_bytes(b"cover")
            self.assert_invalid(workspace, "output must be named slide_01.png")

    def test_validate_rejects_intermediate_pptx(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            (workspace / "quarterly-report.pptx").write_bytes(b"obsolete deck")
            self.assert_invalid(workspace, "must not contain an intermediate PPTX")

    def test_validate_rejects_unknown_and_escaping_chart_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            self.add_chart_package(workspace, slide_id="slide_99")
            self.assert_invalid(workspace, "Chart references unknown slide")

            self.add_chart_package(workspace)
            manifest = json.loads((workspace / "chart_manifest.json").read_text(encoding="utf-8"))
            manifest["charts"][0]["package"]["script"] = "../outside.py"
            (workspace / "chart_manifest.json").write_text(
                json.dumps(manifest) + "\n", encoding="utf-8"
            )
            self.assert_invalid(workspace, "escapes the Project Workspace")

    def test_validate_rejects_planned_chart_without_source_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            spec = {
                "slides": [{"number": 1, "data_charts": ["chart_01"]}, {"number": 2}]
            }
            (workspace / "deck_spec.json").write_text(json.dumps(spec) + "\n", encoding="utf-8")
            self.assert_invalid(workspace, "Missing chart_manifest.json for planned Data Charts")

    def test_validate_accepts_multiple_charts_on_one_slide(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            self.add_chart_package(workspace)
            first_package = workspace / "chart_assets" / "slide_02" / "chart_01"
            second_package = workspace / "chart_assets" / "slide_02" / "chart_02"
            second_package.mkdir(parents=True)
            for name in ("chart.py", "data.csv", "chart.png"):
                (second_package / name).write_bytes((first_package / name).read_bytes())
            manifest = json.loads((workspace / "chart_manifest.json").read_text(encoding="utf-8"))
            second = json.loads(json.dumps(manifest["charts"][0]))
            second["chart_id"] = "chart_02"
            second["semantic_purpose"] = "Show regional growth"
            second["package"] = {
                key: value.replace("chart_01", "chart_02")
                for key, value in second["package"].items()
            }
            manifest["charts"].append(second)
            (workspace / "chart_manifest.json").write_text(
                json.dumps(manifest) + "\n", encoding="utf-8"
            )
            spec = {"slides": [{"number": 1}, {"number": 2, "data_charts": ["chart_01", "chart_02"]}]}
            (workspace / "deck_spec.json").write_text(json.dumps(spec) + "\n", encoding="utf-8")

            result = self.run_cli("validate", str(workspace))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["chart_count"], 2)

    def test_validate_rejects_chart_id_reused_on_another_slide(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            self.add_chart_package(workspace)
            manifest = json.loads((workspace / "chart_manifest.json").read_text(encoding="utf-8"))
            duplicate = json.loads(json.dumps(manifest["charts"][0]))
            duplicate["slide_id"] = "slide_01"
            manifest["charts"].append(duplicate)
            (workspace / "chart_manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            self.assert_invalid(workspace, "Duplicate chart identity: chart_01")

    def test_chart_and_chartless_slides_prepare_record_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "end-to-end"
            for name in ("origin_image", "generated_images", "prompts", "chart_assets"):
                (workspace / name).mkdir(parents=True, exist_ok=True)
            (workspace / "outline.md").write_text("# Approved outline\n", encoding="utf-8")
            (workspace / "deck_spec.json").write_text(
                json.dumps(
                    {
                        "deck_name": "end-to-end",
                        "selected_image_backend": "built-in image tool",
                        "slides": [
                            {"number": 1, "title": "Chart", "data_charts": ["growth"]},
                            {"number": 2, "title": "Summary"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.add_chart_package(workspace, slide_id="slide_01", chart_id="growth")

            prepare = subprocess.run(
                [sys.executable, str(PREPARE_SCRIPT), "--spec", str(workspace / "deck_spec.json"), "--out-dir", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(prepare.returncode, 0, prepare.stderr)
            jobs = json.loads((workspace / "slide_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["slides"][0]["data_charts"][0]["chart_id"], "growth")
            self.assertEqual(jobs["slides"][1]["data_charts"], [])

            for number in (1, 2):
                dispatch = subprocess.run(
                    [sys.executable, str(DISPATCH_SCRIPT), str(workspace), "--slide", str(number), "--agent-id", f"agent-{number}"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(dispatch.returncode, 0, dispatch.stderr)
                outside_source = workspace / f"worker-slide-{number}-outside.png"
                Image.new("RGB", (4, 3), (10, 20, 30)).save(outside_source)
                rejected = subprocess.run(
                    [
                        sys.executable,
                        str(RECORD_SCRIPT),
                        str(workspace),
                        "--slide",
                        str(number),
                        "--agent-id",
                        f"agent-{number}",
                        "--backend-used",
                        "built-in image tool",
                        "--selected-source",
                        str(outside_source),
                        "--qa-note",
                        "visual QA passed",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn("generated_images/ directory", rejected.stderr)
                source = workspace / "generated_images" / f"worker-slide-{number}.png"
                Image.new("RGB", (4, 3), (number * 20, 30, 40)).save(source)
                record = subprocess.run(
                    [
                        sys.executable,
                        str(RECORD_SCRIPT),
                        str(workspace),
                        "--slide",
                        str(number),
                        "--agent-id",
                        f"agent-{number}",
                        "--backend-used",
                        "built-in image tool",
                        "--selected-source",
                        str(source),
                        "--qa-note",
                        "visual QA passed",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(record.returncode, 0, record.stderr)

            handoff = self.run_cli("validate", str(workspace))
            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            self.assertEqual(json.loads(handoff.stdout)["status"], "ready_for_handoff")

    def test_dispatch_rejects_an_idle_slot_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "dispatch-capacity"
            workspace.mkdir(parents=True)
            spec_path = workspace / "deck_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "deck_name": "dispatch-capacity",
                        "selected_image_backend": "built-in image tool",
                        "slides": [
                            {"number": 1, "title": "First"},
                            {"number": 2, "title": "Second"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            prepare = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE_SCRIPT),
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(workspace),
                    "--max-concurrent-slides",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(prepare.returncode, 0, prepare.stderr)

            first = subprocess.run(
                [
                    sys.executable,
                    str(DISPATCH_SCRIPT),
                    str(workspace),
                    "--slide",
                    "1",
                    "--agent-id",
                    "agent-1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(first.returncode, 0, first.stderr)

            second = subprocess.run(
                [
                    sys.executable,
                    str(DISPATCH_SCRIPT),
                    str(workspace),
                    "--slide",
                    "2",
                    "--agent-id",
                    "agent-2",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("No slide dispatch slot is available", second.stderr)

    def test_validate_rejects_opaque_chart_render(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.create_slide_only_workspace(Path(temp_dir))
            self.add_chart_package(workspace)
            opaque = Image.new("RGB", (2, 2), (255, 255, 255))
            opaque.save(workspace / "chart_assets" / "slide_02" / "chart_01" / "chart.png")
            self.assert_invalid(workspace, "Chart render must be a transparent PNG")


if __name__ == "__main__":
    unittest.main()
