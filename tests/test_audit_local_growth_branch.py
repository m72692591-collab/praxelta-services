from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts/audit_local_growth_branch.py"
SPEC = importlib.util.spec_from_file_location("audit_local_growth_branch", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed.stdout.strip()


class LocalGrowthSalvageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "checkout", "-b", "main")
        (self.repo / "README.md").write_text("current\n", encoding="utf-8")
        (self.repo / "index.html").write_text("<h1>current</h1>\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")

        git(self.repo, "checkout", "-b", "historical")
        (self.repo / "README.md").write_text("historical\n", encoding="utf-8")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/LOCAL_GROWTH_PRODUCT.md").write_text(
            "Публичный безопасный продукт ПРАКСЕЛЬТА.\n",
            encoding="utf-8",
        )
        (self.repo / "HUMANITY_GATE_LOCAL_GROWTH_2026-08-13.json").write_text(
            json.dumps({"copy_path": r"C:\\Users\\owner\\secret"}),
            encoding="utf-8",
        )
        (self.repo / "output/pdf").mkdir(parents=True)
        (self.repo / "output/pdf/generated.pdf").write_bytes(b"%PDF-test")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "historical growth")
        git(self.repo, "checkout", "main")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_copies_only_safe_target_only_text(self) -> None:
        payload = MODULE.audit(self.repo, "main", "historical")
        self.assertTrue((self.repo / "docs/LOCAL_GROWTH_PRODUCT.md").exists())
        self.assertIn("docs/LOCAL_GROWTH_PRODUCT.md", payload["copied_files"])
        self.assertFalse(
            (self.repo / "HUMANITY_GATE_LOCAL_GROWTH_2026-08-13.json").exists()
        )
        self.assertFalse((self.repo / "output/pdf/generated.pdf").exists())

    def test_preserves_current_diverged_files(self) -> None:
        payload = MODULE.audit(self.repo, "main", "historical")
        self.assertEqual((self.repo / "README.md").read_text(encoding="utf-8"), "current\n")
        records = {record["path"]: record for record in payload["records"]}
        self.assertEqual(records["README.md"]["state"], "DIVERGED")
        self.assertEqual(
            records["README.md"]["action"],
            "PRESERVE_CURRENT_REVIEW_SEMANTICS",
        )

    def test_report_contains_exact_refs_and_no_destructive_actions(self) -> None:
        payload = MODULE.audit(self.repo, "main", "historical")
        self.assertEqual(payload["current_head"], git(self.repo, "rev-parse", "main"))
        self.assertEqual(
            payload["historical_head"], git(self.repo, "rev-parse", "historical")
        )
        self.assertFalse(payload["destructive_actions_performed"])
        self.assertFalse(payload["branch_deletion_performed"])
        self.assertTrue((self.repo / "docs/repository/LOCAL_GROWTH_SALVAGE.md").exists())


if __name__ == "__main__":
    unittest.main()
