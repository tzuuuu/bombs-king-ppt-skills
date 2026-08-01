from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.util
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = 1
SUPPORTED_SYSTEMS = {"Darwin", "Windows"}
MACOS_POWERPOINT_NAME = "Microsoft PowerPoint.app"


@dataclass(frozen=True)
class DoctorFacts:
    system: str
    machine: str
    python_version: str
    python_supported: bool
    pymupdf_available: bool
    powerpoint_available: bool
    powerpoint_detail: str
    automation_available: bool
    automation_detail: str


class RuntimeProbe:
    """Read runtime prerequisites without starting or controlling PowerPoint."""

    def system(self) -> str:
        return platform.system()

    def machine(self) -> str:
        return platform.machine()

    def python_version(self) -> str:
        return platform.python_version()

    def python_supported(self) -> bool:
        return sys.version_info >= (3, 9)

    def pymupdf_available(self) -> bool:
        return importlib.util.find_spec("fitz") is not None

    def find_command(self, *names: str) -> Optional[str]:
        for name in names:
            command = shutil.which(name)
            if command:
                return command
        return None

    def find_macos_powerpoint(self) -> Optional[str]:
        candidates = (
            Path("/Applications") / MACOS_POWERPOINT_NAME,
            Path.home() / "Applications" / MACOS_POWERPOINT_NAME,
        )
        for candidate in candidates:
            if candidate.is_dir():
                return str(candidate)

        mdfind = self.find_command("mdfind")
        if not mdfind:
            return None
        try:
            result = subprocess.run(
                [mdfind, "kMDItemCFBundleIdentifier == 'com.microsoft.Powerpoint'"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        for line in result.stdout.splitlines():
            candidate = Path(line.strip())
            if candidate.name == MACOS_POWERPOINT_NAME and candidate.is_dir():
                return str(candidate)
        return None

    def windows_powerpoint_registered(self) -> bool:
        try:
            winreg = importlib.import_module("winreg")

            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                r"PowerPoint.Application\CLSID",
            ):
                return True
        except (ImportError, FileNotFoundError, OSError):
            return False


def collect_facts(probe: Optional[RuntimeProbe] = None) -> DoctorFacts:
    runtime = probe or RuntimeProbe()
    system = runtime.system()
    if system == "Darwin":
        powerpoint_path = runtime.find_macos_powerpoint()
        powerpoint_available = powerpoint_path is not None
        powerpoint_detail = powerpoint_path or "Microsoft PowerPoint.app not found"
        automation = runtime.find_command("osascript")
    elif system == "Windows":
        powerpoint_available = runtime.windows_powerpoint_registered()
        powerpoint_detail = "PowerPoint.Application COM registration"
        automation = runtime.find_command("powershell.exe", "pwsh.exe")
    else:
        powerpoint_available = False
        powerpoint_detail = "not applicable"
        automation = None

    return DoctorFacts(
        system=system,
        machine=runtime.machine(),
        python_version=runtime.python_version(),
        python_supported=runtime.python_supported(),
        pymupdf_available=runtime.pymupdf_available(),
        powerpoint_available=powerpoint_available,
        powerpoint_detail=powerpoint_detail,
        automation_available=automation is not None,
        automation_detail=automation or "not found",
    )


def _check(name: str, available: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "available": available, "detail": detail}


def assess(facts: DoctorFacts) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = [
        _check("platform", facts.system in SUPPORTED_SYSTEMS, facts.system),
        _check("python", facts.python_supported, facts.python_version),
        _check("pymupdf", facts.pymupdf_available, "import fitz"),
        _check("powerpoint", facts.powerpoint_available, facts.powerpoint_detail),
        _check(
            "automation_controller",
            facts.automation_available,
            facts.automation_detail,
        ),
    ]
    error_priorities = [
        ("platform", "UNSUPPORTED_PLATFORM"),
        ("python", "UNSUPPORTED_PYTHON"),
        ("pymupdf", "MISSING_PDF_RUNTIME"),
        ("powerpoint", "POWERPOINT_NOT_FOUND"),
        ("automation_controller", "AUTOMATION_UNAVAILABLE"),
    ]
    failed_names = {check["name"] for check in checks if not check["available"]}

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "doctor",
        "status": "ok" if not failed_names else "error",
        "platform": {"system": facts.system, "machine": facts.machine},
        "checks": checks,
        "automation_permission": {
            "state": (
                "not_applicable"
                if facts.system not in SUPPORTED_SYSTEMS
                else "unverified"
                if facts.automation_available
                else "unavailable"
            ),
            "detail": (
                "Plain doctor does not open PowerPoint or send an automation event; "
                "verify permission with the render smoke test before inspection."
                if facts.system in SUPPORTED_SYSTEMS and facts.automation_available
                else "Automation permission cannot be verified on this runtime."
            ),
        },
    }
    if failed_names:
        error_code = next(
            code for name, code in error_priorities if name in failed_names
        )
        payload["error_code"] = error_code
        payload["repair_action"] = {
            "AUTOMATION_UNAVAILABLE": (
                "Make PowerShell available, then run doctor again."
                if facts.system == "Windows"
                else "Restore the macOS osascript command, then run doctor again."
            ),
            "MISSING_PDF_RUNTIME": (
                "Install the skill CLI with its PyMuPDF dependency, then run doctor again."
            ),
            "POWERPOINT_NOT_FOUND": (
                "Install desktop Microsoft PowerPoint, then run doctor again."
            )
        }.get(error_code, "Resolve failed checks and run doctor again.")
    return payload


def diagnose() -> Dict[str, Any]:
    return assess(collect_facts())
