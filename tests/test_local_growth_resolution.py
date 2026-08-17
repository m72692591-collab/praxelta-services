from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_local_growth_resolution.py"
RESOLUTION = ROOT / "operations/salvage/local-service-growth-v3/DIVERGED_RESOLUTION.json"
STATUS = ROOT / "operations/salvage/local-service-growth-v3/INTEGRATION_STATUS.json"

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


def test_owner_product_decision_gate_cannot_be_removed() -> None:
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
