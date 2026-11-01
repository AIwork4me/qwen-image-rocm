"""Regression: quality.md must describe the ACTUAL baseline, never a
hardcoded one. The r1-triple gate ran against E8 (turbo int8 + bf16 TE + ck,
8 steps) but its quality.md claimed 'bf16, 40 steps' — a mislabel that made
a fidelity gate read like a bf16 comparison.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench.quality_gate import describe_baseline, write_quality_md  # noqa: E402


def test_desc_derived_from_baseline_records():
    # e8's records dir exists and says int8-convrot / 8 steps
    d = describe_baseline("results/raw/2026-11-01-e8-turbo-int8-ck")
    assert "int8-convrot" in d
    assert "8 steps" in d
    assert "bf16, 40 steps" not in d
    assert "turbo_int8_convrot" in d and "TE bf16" in d


def test_desc_true_bf16_baseline_still_shows_bf16():
    d = describe_baseline("results/raw/2026-10-31-e1-control")
    assert "bf16" in d and "40 steps" in d


def test_desc_override_wins():
    d = describe_baseline("results/raw/2026-11-01-e8-turbo-int8-ck", "E8 as shipped")
    assert d == "E8 as shipped"


def test_desc_fails_safe_when_no_records(tmp_path):
    d = describe_baseline(tmp_path / "nope")
    assert "no run records found" in d


def test_write_quality_md_uses_derived_desc(tmp_path):
    out = tmp_path / "q.md"
    write_quality_md(
        out, "exp-x", "fidelity", {}, None,
        "results/raw/2026-11-01-e8-turbo-int8-ck", "results/raw/exp-x",
    )
    text = out.read_text(encoding="utf-8")
    assert "- Baseline: " in text
    assert "int8-convrot" in text and "8 steps" in text
    assert "(bf16, 40 steps)" not in text  # the old hardcoded label


def test_committed_r1_quality_md_labels_the_real_baseline():
    md = (Path(__file__).resolve().parents[1]
          / "bench" / "results" / "2026-11-01-r1-triple" / "quality.md")
    if not md.exists():
        import pytest

        pytest.skip("evidence dir not present")
    text = md.read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("- Baseline:"))
    assert "e8-turbo-int8-ck" in line
    assert "bf16, 40 steps" not in line
    assert "8 steps" in line and "int8-convrot" in line


def test_r1_lpips_mapping_matches_recorded_values():
    """Pin the p1/p2/p3 LPIPS mapping so docs cannot transpose it again."""
    md = (Path(__file__).resolve().parents[1]
          / "bench" / "results" / "2026-11-01-r1-triple" / "quality.md")
    if not md.exists():
        import pytest

        pytest.skip("evidence dir not present")
    rows = {}
    for line in md.read_text(encoding="utf-8").splitlines():
        if line.startswith("| p"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows[cells[0]] = float(cells[1])
    assert round(rows["p1-zh-scene"], 4) == 0.0583
    assert round(rows["p2-en-scene"], 4) == 0.0115
    assert round(rows["p3-poster-text"], 4) == 0.0137
    # and a JSON echo so tooling can consume the same numbers
    echo = json.loads((md.parent / "quality.json").read_text(encoding="utf-8"))
    assert echo["baseline_experiment"] == "p3-turbo-int8-ck-1024x1024"
    assert round(echo["median"]["p1-zh-scene"], 4) == rows["p1-zh-scene"]
