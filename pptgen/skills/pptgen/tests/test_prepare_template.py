from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "prepare_template.py"
MODULE_SPEC = importlib.util.spec_from_file_location("prepare_template", SCRIPT_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
prepare_template = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(prepare_template)


class PrepareTemplateTests(unittest.TestCase):
    def test_prepare_destination_preserves_ppt_source_extension_and_fixed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "client-master.ppt"
            source.write_bytes(b"legacy powerpoint source")

            copied, pdf, manifest = prepare_template._prepare_destination(
                source,
                root / "deck",
                overwrite=False,
            )

            self.assertEqual(copied, (root / "deck" / "template" / "template.ppt").resolve())
            self.assertEqual(pdf, (root / "deck" / "template" / "template.pdf").resolve())
            self.assertEqual(
                manifest,
                (root / "deck" / "template" / "template_manifest.json").resolve(),
            )
            self.assertEqual(copied.read_bytes(), source.read_bytes())

    def test_resolve_source_rejects_non_powerpoint_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "not-a-template.pdf"
            source.write_bytes(b"pdf")

            with self.assertRaises(prepare_template.TemplateError):
                prepare_template._resolve_source(source)


if __name__ == "__main__":
    unittest.main()
