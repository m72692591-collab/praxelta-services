from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_local_growth_resolution.py"
RESOLUTION = ROOT / "operations/salvage/local-service-growth-v3/DIVERGED_RESOLUTION.json"
STATUS = ROOT / "operations/salvage/local-service-growth-v3/INTEGRATION_STATUS.json"
SUCCESSOR = ROOT / "operations/salvage/local-service-growth-v3/ACTIVE_PRODUCT_V2_SUCCESSOR.json"

spec = importlib.util.spec_from_file_location("local_growth_resolution", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_resolution_passes_without_remote_source_lookup() -> None:
    assert validator.validate(ROOT, load(RESOLUTION), load(STATUS)) == []


def test_every_diverged_path_is_resolved_exactly_once() -> None:
    data = load(RESOLUTION)
    paths = [row["path"] for row in data["resolutions"]]
    assert len(paths) == 13
    assert len(paths) == len(set(paths))
    assert set(paths) == validator.EXPECTED_PATHS


def test_current_blob_drift_is_blocked() -> None:
    data = load(RESOLUTION)
    changed = copy.deepcopy(data)
    changed["resolutions"][0]["current_blob"] = "0" * 40
    errors = validator.validate(ROOT, changed, load(STATUS))
    assert any("current blob drift" in error for error in errors)


def test_source_blob_must_have_git_sha_format() -> None:
    data = load(RESOLUTION)
    changed = copy.deepcopy(data)
    changed["resolutions"][0]["source_blob"] = "bad"
    errors = validator.validate(ROOT, changed, load(STATUS))
    assert any("invalid source blob SHA" in error for error in errors)


def test_resolution_cannot_unlock_launch() -> None:
    data = load(RESOLUTION)
    changed = copy.deepcopy(data)
    changed["summary"]["product_launch_unlocked"] = True
    errors = validator.validate(ROOT, changed, load(STATUS))
    assert any("product_launch_unlocked" in error for error in errors)


def test_resolution_cannot_enable_payments() -> None:
    data = load(RESOLUTION)
    changed = copy.deepcopy(data)
    changed["summary"]["payments_enabled"] = True
    errors = validator.validate(ROOT, changed, load(STATUS))
    assert any("payments_enabled" in error for error in errors)


def test_historical_owner_product_decision_gate_cannot_be_removed() -> None:
    data = load(RESOLUTION)
    changed = copy.deepcopy(data)
    changed["next_gate"]["status"] = "ACTIVE_PRODUCT"
    errors = validator.validate(ROOT, changed, load(STATUS))
    assert any("owner product decision gate drift" in error for error in errors)


def test_integration_status_must_match_exact_diverged_set() -> None:
    status = load(STATUS)
    changed = copy.deepcopy(status)
    changed["diverged_paths_requiring_semantic_resolution"] = changed[
        "diverged_paths_requiring_semantic_resolution"
    ][1:]
    errors = validator.validate(ROOT, load(RESOLUTION), changed)
    assert any("diverged set" in error for error in errors)


def test_active_product_successor_links_exact_historical_and_current_blobs() -> None:
    successor = load(SUCCESSOR)
    assert successor["historical_path"] == "index.html"
    assert successor["historical_current_blob"] == (
        "b9841e994cdab3b21a299f24884ed19ca4a750c3"
    )
    assert successor["successor_blob"] == (
        "6b338f78c75bfb6b14577cfb4438b9d96a715d06"
    )
    assert successor["scope"]["live_payments"] is False
    assert successor["scope"]["first_paid_case_verified"] is False
    assert successor["scope"]["revenue_verified"] is False
    assert successor["scope"]["profit_verified"] is False


def test_successor_blob_drift_is_blocked() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "repo"
        shutil.copytree(
            ROOT,
            root,
            ignore=shutil.ignore_patterns(
                ".git",
                ".praxelta-local",
                "__pycache__",
                "*.pyc",
                ".pytest_cache",
            ),
        )
        path = (
            root
            / "operations"
            / "salvage"
            / "local-service-growth-v3"
            / "ACTIVE_PRODUCT_V2_SUCCESSOR.json"
        )
        successor = load(path)
        successor["successor_blob"] = "0" * 40
        path.write_text(
            json.dumps(successor, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        errors = validator.validate(
            root,
            load(
                root
                / "operations"
                / "salvage"
                / "local-service-growth-v3"
                / "DIVERGED_RESOLUTION.json"
            ),
            load(
                root
                / "operations"
                / "salvage"
                / "local-service-growth-v3"
                / "INTEGRATION_STATUS.json"
            ),
        )
        assert any("successor blob drift" in error for error in errors)


def test_successor_cannot_enable_unproven_commercial_gate() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "repo"
        shutil.copytree(
            ROOT,
            root,
            ignore=shutil.ignore_patterns(
                ".git",
                ".praxelta-local",
                "__pycache__",
                "*.pyc",
                ".pytest_cache",
            ),
        )
        registry_path = (
            root
            / "operations"
            / "products"
            / "LOCAL_GROWTH_PRODUCT_DECISION_V2.json"
        )
        registry = load(registry_path)
        registry["commercial_gates"]["first_paid_case_verified"] = True
        registry_path.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        errors = validator.validate(
            root,
            load(
                root
                / "operations"
                / "salvage"
                / "local-service-growth-v3"
                / "DIVERGED_RESOLUTION.json"
            ),
            load(
                root
                / "operations"
                / "salvage"
                / "local-service-growth-v3"
                / "INTEGRATION_STATUS.json"
            ),
        )
        assert any(
            "unproven gate enabled: first_paid_case_verified" in error
            for error in errors
        )
