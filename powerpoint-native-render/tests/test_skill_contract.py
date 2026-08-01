from __future__ import annotations

from pathlib import Path
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SKILL = PACKAGE_ROOT / "skills" / "inspect-powerpoint-natively" / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_advertises_each_approved_branch_once(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]

        self.assertIn("name: inspect-powerpoint-natively", frontmatter)
        self.assertNotIn("TODO", text)
        for branch in (
            "read or summarize visible slides",
            "analyze presentation style or layout",
            "conversion or reconstruction reference",
            "compare presentation visuals",
            "visual QA",
        ):
            with self.subTest(branch=branch):
                self.assertEqual(frontmatter.count(branch), 1)


if __name__ == "__main__":
    unittest.main()
