from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
from typing import Optional


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CLI_ROOT = PACKAGE_ROOT / "skills" / "inspect-powerpoint-natively" / "cli"
sys.path.insert(0, str(CLI_ROOT))

from powerpoint_native_render.doctor import (  # noqa: E402
    DoctorFacts,
    RuntimeProbe,
    assess,
    collect_facts,
)


class FakeProbe(RuntimeProbe):
    def __init__(
        self,
        *,
        system: str,
        macos_powerpoint: Optional[str] = None,
        windows_powerpoint: bool = False,
        automation_command: Optional[str] = None,
    ) -> None:
        self._system = system
        self._macos_powerpoint = macos_powerpoint
        self._windows_powerpoint = windows_powerpoint
        self._automation_command = automation_command

    def system(self) -> str:
        return self._system

    def machine(self) -> str:
        return "test-machine"

    def python_version(self) -> str:
        return "3.12.0"

    def python_supported(self) -> bool:
        return True

    def pymupdf_available(self) -> bool:
        return True

    def find_macos_powerpoint(self) -> Optional[str]:
        return self._macos_powerpoint

    def windows_powerpoint_registered(self) -> bool:
        return self._windows_powerpoint

    def find_command(self, *names: str) -> Optional[str]:
        return self._automation_command


class DoctorCliTests(unittest.TestCase):
    def test_doctor_always_emits_one_versioned_json_object(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(CLI_ROOT)

        result = subprocess.run(
            [sys.executable, "-m", "powerpoint_native_render.cli", "doctor"],
            cwd=PACKAGE_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "doctor")
        self.assertIn(payload["status"], {"ok", "error"})
        self.assertIn(result.returncode, {0, 1})
        self.assertEqual(result.stdout.count("\n"), 1)

    def test_skill_local_cli_installs_and_exposes_the_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            copied_cli = temporary_root / "cli"
            virtualenv = temporary_root / "venv"
            shutil.copytree(CLI_ROOT, copied_cli)
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(virtualenv)

            if sys.platform == "win32":
                python = virtualenv / "Scripts" / "python.exe"
                command = virtualenv / "Scripts" / "powerpoint-native-render.exe"
            else:
                python = virtualenv / "bin" / "python"
                command = virtualenv / "bin" / "powerpoint-native-render"

            install = subprocess.run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--no-build-isolation",
                    "--editable",
                    str(copied_cli),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            result = subprocess.run(
                [str(command), "doctor"],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["command"], "doctor")
            self.assertIn(result.returncode, {0, 1})


class DoctorAssessmentTests(unittest.TestCase):
    def test_collect_facts_uses_macos_adapter_discovery(self) -> None:
        facts = collect_facts(
            FakeProbe(
                system="Darwin",
                macos_powerpoint="/Users/test/Applications/Microsoft PowerPoint.app",
                automation_command="/usr/bin/osascript",
            )
        )

        self.assertTrue(facts.powerpoint_available)
        self.assertEqual(
            facts.powerpoint_detail,
            "/Users/test/Applications/Microsoft PowerPoint.app",
        )
        self.assertTrue(facts.automation_available)

    def test_collect_facts_uses_windows_adapter_discovery(self) -> None:
        facts = collect_facts(
            FakeProbe(
                system="Windows",
                windows_powerpoint=True,
                automation_command="C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
            )
        )

        self.assertTrue(facts.powerpoint_available)
        self.assertEqual(
            facts.powerpoint_detail,
            "PowerPoint.Application COM registration",
        )
        self.assertTrue(facts.automation_available)

    def test_collect_facts_marks_linux_discovery_not_applicable(self) -> None:
        facts = collect_facts(FakeProbe(system="Linux"))

        self.assertFalse(facts.powerpoint_available)
        self.assertEqual(facts.powerpoint_detail, "not applicable")
        self.assertFalse(facts.automation_available)

    def test_supported_macos_and_windows_facts_are_healthy(self) -> None:
        for facts in (
            DoctorFacts(
                system="Darwin",
                machine="arm64",
                python_version="3.12.0",
                python_supported=True,
                pymupdf_available=True,
                powerpoint_available=True,
                powerpoint_detail="/Applications/Microsoft PowerPoint.app",
                automation_available=True,
                automation_detail="/usr/bin/osascript",
            ),
            DoctorFacts(
                system="Windows",
                machine="AMD64",
                python_version="3.11.0",
                python_supported=True,
                pymupdf_available=True,
                powerpoint_available=True,
                powerpoint_detail="PowerPoint.Application COM registration",
                automation_available=True,
                automation_detail="powershell.exe",
            ),
        ):
            with self.subTest(system=facts.system):
                payload = assess(facts)
                self.assertEqual(payload["status"], "ok")
                self.assertNotIn("error_code", payload)
                self.assertEqual(
                    payload["automation_permission"]["state"], "unverified"
                )
                self.assertIn(
                    "does not open PowerPoint",
                    payload["automation_permission"]["detail"],
                )

    def test_linux_is_an_unsupported_platform(self) -> None:
        payload = assess(
            DoctorFacts(
                system="Linux",
                machine="x86_64",
                python_version="3.12.0",
                python_supported=True,
                pymupdf_available=True,
                powerpoint_available=False,
                powerpoint_detail="not applicable",
                automation_available=False,
                automation_detail="not applicable",
            )
        )

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error_code"], "UNSUPPORTED_PLATFORM")

    def test_missing_powerpoint_has_a_specific_repair_action(self) -> None:
        payload = assess(
            DoctorFacts(
                system="Darwin",
                machine="arm64",
                python_version="3.12.0",
                python_supported=True,
                pymupdf_available=True,
                powerpoint_available=False,
                powerpoint_detail="/Applications/Microsoft PowerPoint.app",
                automation_available=True,
                automation_detail="/usr/bin/osascript",
            )
        )

        self.assertEqual(payload["error_code"], "POWERPOINT_NOT_FOUND")
        self.assertIn("Microsoft PowerPoint", payload["repair_action"])

    def test_missing_pdf_runtime_has_a_specific_repair_action(self) -> None:
        payload = assess(
            DoctorFacts(
                system="Windows",
                machine="AMD64",
                python_version="3.11.0",
                python_supported=True,
                pymupdf_available=False,
                powerpoint_available=True,
                powerpoint_detail="PowerPoint.Application COM registration",
                automation_available=True,
                automation_detail="powershell.exe",
            )
        )

        self.assertEqual(payload["error_code"], "MISSING_PDF_RUNTIME")
        self.assertIn("PyMuPDF", payload["repair_action"])

    def test_missing_automation_names_the_platform_command(self) -> None:
        payload = assess(
            DoctorFacts(
                system="Windows",
                machine="AMD64",
                python_version="3.11.0",
                python_supported=True,
                pymupdf_available=True,
                powerpoint_available=True,
                powerpoint_detail="PowerPoint.Application COM registration",
                automation_available=False,
                automation_detail="not found",
            )
        )

        self.assertEqual(payload["error_code"], "AUTOMATION_UNAVAILABLE")
        self.assertIn("PowerShell", payload["repair_action"])


if __name__ == "__main__":
    unittest.main()
