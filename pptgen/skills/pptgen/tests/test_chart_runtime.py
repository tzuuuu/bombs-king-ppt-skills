from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class ManagedChartRuntimeTests(unittest.TestCase):
    def test_local_snapshot_reproduces_transparent_chart_render(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = Path(temp_dir)
            (package / "data.csv").write_text(
                "month,value\nJan,10\nFeb,12\nMar,15\n",
                encoding="utf-8",
            )
            (package / "chart.py").write_text(
                """from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

root = Path(__file__).resolve().parent
data = pd.read_csv(root / "data.csv")
sns.set_theme(style="ticks")
figure, axis = plt.subplots(figsize=(6, 3))
sns.lineplot(data=data, x="month", y="value", marker="o", color="#1f77b4", ax=axis)
axis.set_xlabel("Month")
axis.set_ylabel("Value")
figure.savefig(root / "chart.png", transparent=True, bbox_inches="tight")
plt.close(figure)
""",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["MPLCONFIGDIR"] = str(package / ".matplotlib")
            env["MPLBACKEND"] = "Agg"
            env["XDG_CACHE_HOME"] = str(package / ".cache")

            result = subprocess.run(
                [sys.executable, str(package / "chart.py")],
                cwd=package,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(package / "chart.png") as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.mode, "RGBA")
                self.assertLess(image.getchannel("A").getextrema()[0], 255)


if __name__ == "__main__":
    unittest.main()
