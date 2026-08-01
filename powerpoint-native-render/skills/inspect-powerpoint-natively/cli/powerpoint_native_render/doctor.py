from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import platform
import shutil
import sys
from typing import Any, Dict, List


SCHEMA_VERSION = 1
SUPPORTED_SYSTEMS = {"Darwin", "Windows"}
MACOS_POWERPOINT = Path("/Applications/Microsoft PowerPoint.app")


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


def _windows_powerpoint_registered() -> bool:
    try:
        import winreg  # type: ignore[import-not-found]

        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            r"PowerPoint.Application\CLSID",
        ):
            return True
    except (ImportError, FileNotFoundError, OSError):
        return False


def collect_facts() -> DoctorFacts:
    system = platform.system()
    if system == "Darwin":
        powerpoint_available = MACOS_POWERPOINT.is_dir()
        powerpoint_detail = str(MACOS_POWERPOINT)
        automation = shutil.which("osascript")
    elif system == "Windows":
        powerpoint_available = _windows_powerpoint_registered()
        powerpoint_detail = "PowerPoint.Application COM registration"
        automation = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    else:
        powerpoint_available = False
        powerpoint_detail = "not applicable"
        automation = None

    return DoctorFacts(
        system=system,
        machine=platform.machine(),
        python_version=platform.python_version(),
        python_supported=sys.version_info >= (3, 9),
        pymupdf_available=importlib.util.find_spec("fitz") is not None,
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
        _check("automation", facts.automation_available, facts.automation_detail),
    ]
    error_priorities = [
        ("platform", "UNSUPPORTED_PLATFORM"),
        ("python", "UNSUPPORTED_PYTHON"),
        ("pymupdf", "MISSING_PDF_RUNTIME"),
        ("powerpoint", "POWERPOINT_NOT_FOUND"),
        ("automation", "AUTOMATION_UNAVAILABLE"),
    ]
    failed_names = {check["name"] for check in checks if not check["available"]}

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "doctor",
        "status": "ok" if not failed_names else "error",
        "platform": {"system": facts.system, "machine": facts.machine},
        "checks": checks,
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
