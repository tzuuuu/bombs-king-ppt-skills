from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def workflow_gate(markdown: str, semantic_name: str) -> str:
    pattern = re.compile(
        rf"^\d+\.\s+\*\*{re.escape(semantic_name)}\b[^\n]*\n.*?(?=^\d+\.\s+\*\*|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    if not match:
        raise AssertionError(f"Missing workflow gate: {semantic_name}")
    return match.group(0)


class SkillInformationHierarchyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.workflow_gates = (SKILL_ROOT / "docs" / "workflow-gates-and-progress.md").read_text(
            encoding="utf-8"
        )
        cls.subagent_reference = (
            SKILL_ROOT / "docs" / "slide-generation-and-subagents.md"
        ).read_text(encoding="utf-8")

    def test_skill_is_the_single_source_for_gate_order_and_completion(self) -> None:
        self.assertIn("`SKILL.md` owns the gate order and completion criteria", self.workflow_gates)
        self.assertNotIn("Phase order:", self.workflow_gates)
        self.assertNotIn("Completion evidence:", self.workflow_gates)
        self.assertNotIn("**Delegation boundary:**", self.skill)
        self.assertNotIn("**State evidence:**", self.skill)
        self.assertNotIn("**Blocker behavior:**", self.skill)

    def test_skill_identity_matches_folder_and_active_documentation(self) -> None:
        self.assertEqual(SKILL_ROOT.name, "pptgen")
        self.assertIn("\nname: pptgen\n", self.skill)

        repository = SKILL_ROOT.parents[1]
        active_docs = [
            repository / "README.md",
            repository / "README_en.md",
            repository / "README_ko.md",
            *(repository / "docs").glob("*.md"),
            *(repository / "docs" / "en").glob("*.md"),
            *(repository / "docs" / "ko").glob("*.md"),
        ]
        stale_identity = (
            "skills/codex-ppt",
            "--skill codex-ppt",
            "codex-ppt skill",
            "`codex-ppt`",
        )
        for path in active_docs:
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                for stale in stale_identity:
                    self.assertNotIn(stale, content)

        changelog = (repository / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Rename the installable skill from `codex-ppt` to `pptgen`", changelog)

    def test_chart_details_are_disclosed_only_for_the_chart_branch(self) -> None:
        chart_reference = SKILL_ROOT / "docs" / "data-charts.md"
        self.assertTrue(chart_reference.is_file())
        charts = chart_reference.read_text(encoding="utf-8")
        package_gate = workflow_gate(self.skill, "Package gate")
        self.assertIn("docs/data-charts.md", package_gate)
        for detail in ("Matplotlib", "pandas", "NumPy", "Seaborn", "Chart-only render"):
            self.assertNotIn(detail, self.skill)
        for detail in ("Matplotlib", "pandas", "NumPy", "Seaborn", "transparent PNG"):
            self.assertIn(detail, charts)

    def test_source_gate_requires_observable_brief_and_asset_inventory(self) -> None:
        source_gate = workflow_gate(self.skill, "Source gate")
        for evidence in (
            "user-visible source brief",
            "topic",
            "audience",
            "goal",
            "inclusions",
            "exclusions",
            "brand constraints",
            "page count",
            "asset inventory",
            "source or path",
            "intended role",
            "availability",
        ):
            self.assertIn(evidence, source_gate)

    def test_user_visible_source_gate_is_documented_in_every_language(self) -> None:
        repository = SKILL_ROOT.parents[1]
        expected_terms = {
            repository / "README.md": ("来源简报", "资产清单"),
            repository / "README_en.md": ("source brief", "asset inventory"),
            repository / "README_ko.md": ("소스 브리프", "자산 목록"),
            repository / "docs" / "workflow.md": ("来源简报", "资产清单"),
            repository / "docs" / "en" / "workflow.md": ("source brief", "asset inventory"),
            repository / "docs" / "ko" / "workflow.md": ("소스 브리프", "자산 목록"),
        }
        for path, terms in expected_terms.items():
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                for term in terms:
                    self.assertIn(term, content)
        changelog = (repository / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("user-visible source brief and asset inventory", changelog)

    def test_production_details_live_only_in_subagent_reference(self) -> None:
        production_gate = workflow_gate(self.skill, "Production gate")
        detailed_rules = {
            "one worker per remaining page": "Use one subagent per remaining slide image job",
            "parent retains ownership": "Parent agent responsibilities",
            "record_slide_dispatch.py": "record_slide_dispatch.py",
            "record_slide_result.py": "record_slide_result.py",
            "record_slide_blocker.py": "record_slide_blocker.py",
        }
        for skill_detail, reference_detail in detailed_rules.items():
            self.assertNotIn(skill_detail, production_gate)
            self.assertIn(reference_detail, self.subagent_reference)

    def test_source_gate_requires_resolved_values_or_approved_assumptions(self) -> None:
        source_gate = workflow_gate(self.skill, "Source gate")
        self.assertIn("user-approved assumption", source_gate)
        self.assertIn("unresolved open question", source_gate)
        self.assertNotIn("value or an explicit open question", source_gate)

    def test_workflow_gate_uses_semantic_name_instead_of_number(self) -> None:
        markdown = (
            "12. **Source gate — establish the brief.**\nSource evidence.\n\n"
            "40. **Outline gate — approve the narrative.**\nOutline evidence.\n"
        )
        self.assertIn("Source evidence.", workflow_gate(markdown, "Source gate"))
        with self.assertRaisesRegex(AssertionError, "Missing workflow gate: QA gate"):
            workflow_gate(markdown, "QA gate")

    def test_gate_boundary_requires_one_confirmation_then_uninterrupted_next_gate(self) -> None:
        self.assertIn("Gate boundary protocol", self.skill)
        self.assertIn("one affirmative confirmation", self.skill)
        self.assertIn("do not pause for another user response", self.skill)
        self.assertIn("Gate boundary protocol", self.workflow_gates)
        self.assertIn("uninterrupted", self.workflow_gates)

    def test_gates_six_seven_eight_parallelize_page_scoped_subagents(self) -> None:
        for gate_name in ("Package gate", "Production gate", "QA gate"):
            with self.subTest(gate=gate_name):
                gate = workflow_gate(self.skill, gate_name)
                self.assertIn("subagent", gate.lower())
                self.assertIn("parallel", gate.lower())
                self.assertIn("page", gate.lower())
        for marker in ("Gate 6", "Gate 7", "Gate 8"):
            self.assertIn(marker, self.subagent_reference)


if __name__ == "__main__":
    unittest.main()
