from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SKILL_ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = SKILL_ROOT / "scripts" / "prepare_slide_prompts.py"


class PrepareSlidePromptsCliTests(unittest.TestCase):
    def test_default_page_worker_capacity_is_30(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "default-capacity-deck"
            spec_path = workspace / "deck_spec.json"
            workspace.mkdir(parents=True)
            spec_path.write_text(
                json.dumps(
                    {
                        "deck_name": "default-capacity-deck",
                        "selected_image_backend": "built-in image tool",
                        "slides": [{"number": 1, "title": "Overview"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE_SCRIPT),
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(workspace),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            jobs = json.loads((workspace / "slide_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["max_concurrent_slides"], 30)
            self.assertEqual(jobs["candidate_output_dir"], "generated_images")
            self.assertTrue((workspace / "generated_images").is_dir())
            prompt_job = json.loads(
                (workspace / "prompts" / "slide_01.json").read_text(encoding="utf-8")
            )
            self.assertEqual(prompt_job["candidate_output_dir"], "generated_images")

    def test_planned_data_chart_becomes_required_slide_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "growth-deck"
            package = workspace / "chart_assets" / "slide_01" / "chart_01"
            package.mkdir(parents=True)
            (package / "chart.py").write_text("# reproducible chart generator\n", encoding="utf-8")
            (package / "data.csv").write_text("month,value\nJan,10\n", encoding="utf-8")
            image = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
            image.putpixel((0, 0), (31, 119, 180, 255))
            image.save(package / "chart.png")
            manifest = {
                "schema_version": 1,
                "charts": [
                    {
                        "slide_id": "slide_01",
                        "chart_id": "chart_01",
                        "chart_type": "line",
                        "semantic_purpose": "Show monthly growth",
                        "source_description": "Approved report data",
                        "required_downstream": True,
                        "package": {
                            "script": "chart_assets/slide_01/chart_01/chart.py",
                            "data": "chart_assets/slide_01/chart_01/data.csv",
                            "image": "chart_assets/slide_01/chart_01/chart.png",
                        },
                    }
                ],
            }
            (workspace / "chart_manifest.json").write_text(
                json.dumps(manifest) + "\n", encoding="utf-8"
            )
            spec = {
                "deck_name": "growth-deck",
                "selected_image_backend": "built-in image tool",
                "slides": [
                    {
                        "number": 1,
                        "title": "Growth",
                        "data_charts": ["chart_01"],
                    }
                ],
            }
            spec_path = workspace / "deck_spec.json"
            spec_path.write_text(json.dumps(spec) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE_SCRIPT),
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(workspace),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            job = json.loads((workspace / "prompts" / "slide_01.json").read_text(encoding="utf-8"))
            chart_image = str((package / "chart.png").resolve())
            self.assertIn(
                {
                    "path": chart_image,
                    "role": "Data Chart: Show monthly growth",
                    "fidelity": "required numerical source; preserve chart meaning and visual identity",
                    "chart_id": "chart_01",
                },
                job["input_images"],
            )
            self.assertEqual(job["data_charts"][0]["chart_id"], "chart_01")
            self.assertIn("Chart Source Package", job["prompt"])
            jobs = json.loads((workspace / "slide_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["slides"][0]["data_charts"][0]["chart_id"], "chart_01")


if __name__ == "__main__":
    unittest.main()
