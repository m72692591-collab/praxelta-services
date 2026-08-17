from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_repository_hygiene.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_repository_hygiene",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "registry_id": "PRAXELTA_EPHEMERAL_WORKFLOW_RETIREMENT_V1",
        "canonical_branch": "main",
        "policy": {
            "one_shot_workflows_allowed_in_main": False,
            "git_history_preserved": True,
            "branch_deletion_performed": False,
            "product_content_changed": False,
            "destructive_git_used": False,
        },
        "retired_workflows": [
            {
                "path": path,
                "blob_sha": sha,
                "status": "RETIRED_FROM_MAIN",
                "reason": "evidence",
            }
            for path, sha in VALIDATOR.EXPECTED.items()
        ],
    }


def valid_receipt() -> dict:
    return {
        "repository": "m72692591-collab/praxelta-services",
        "status": "BLOCKED_BY_REPOSITORY_ADMINISTRATION_PERMISSION",
        "expected_description": (
            "ПРАКСЕЛЬТА — управляемое продвижение локальных услуг и учёт обращений"
        ),
        "expected_homepage": (
            "https://m72692591-collab.github.io/praxelta-services/"
        ),
        "secrets_recorded": False,
    }


class RepositoryHygieneTests(unittest.TestCase):
    def test_valid_manifest_passes(self) -> None:
        self.assertEqual([], VALIDATOR.validate_manifest(valid_manifest()))

    def test_changed_blob_sha_fails(self) -> None:
        data = valid_manifest()
        data["retired_workflows"][0]["blob_sha"] = "0" * 40
        self.assertTrue(VALIDATOR.validate_manifest(data))

    def test_valid_receipt_passes(self) -> None:
        self.assertEqual([], VALIDATOR.validate_receipt(valid_receipt()))

    def test_receipt_cannot_record_secrets(self) -> None:
        data = valid_receipt()
        data["secrets_recorded"] = True
        errors = VALIDATOR.validate_receipt(data)
        self.assertTrue(any("must not record secrets" in error for error in errors))

    def test_one_shot_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / ".github/workflows/one-shot-test.yml"
            path.parent.mkdir(parents=True)
            path.write_text("name: test\n", encoding="utf-8")
            self.assertEqual(
                [".github/workflows/one-shot-test.yml"],
                VALIDATOR.find_one_shots(root),
            )

    def test_permanent_workflow_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / ".github/workflows/quality.yml"
            path.parent.mkdir(parents=True)
            path.write_text("name: quality\n", encoding="utf-8")
            self.assertEqual([], VALIDATOR.find_one_shots(root))

    def test_bytecode_is_detected(self) -> None:
        self.assertEqual(
            ["scripts/__pycache__/guard.cpython-312.pyc"],
            VALIDATOR.find_bytecode(
                [
                    "scripts/__pycache__/guard.cpython-312.pyc",
                    "scripts/guard.py",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
