"""Quality-gate anti-regression suite (final-closure round, cases 1-6).

The generator must describe whatever baseline was actually used — never
assume bf16-40 — and fidelity LPIPS must never read as an absolute quality
score. Historical phase-3 quality.md files (whose baseline really WAS the
bf16-40 control) are frozen evidence and untouched by this suite.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench.quality_gate import (  # noqa: E402
    SEMANTICS_NOTE,
    describe_baseline,
)

R1 = Path(__file__).resolve().parents[1] / "bench" / "results" / "2026-11-01-r1-triple"


def _write_record(d: Path, **fields) -> None:
    base = {
        "experiment": "x", "precision": "bf16", "steps": 40,
        "unet": "qwen_image_2.1_bf16.safetensors",
        "clip": "qwen3vl_8b_bf16.safetensors",
    }
    base.update(fields)
    (d / "seed-42-r0.json").write_text(json.dumps(base), encoding="utf-8")


# Case 1 — a true bf16-40 baseline must display as bf16-40
def test_case1_true_bf16_baseline_shows_bf16_40():
    d = describe_baseline("results/raw/2026-10-31-e1-control")
    assert "bf16" in d and "40 steps" in d


# Case 2 — the E8 baseline must display its actual config
def test_case2_e8_baseline_shows_e8_config():
    d = describe_baseline("results/raw/2026-11-01-e8-turbo-int8-ck")
    assert "int8-convrot" in d and "8 steps" in d and "turbo_int8_convrot" in d
    assert "TE bf16" in d  # E8's text encoder was bf16 — say so precisely


# Case 3 — a future non-bf16 baseline: description follows records, and the
# fidelity NOTE never hardcodes a bf16 reference
def test_case3_future_non_bf16_baseline(tmp_path):
    recs = tmp_path / "bench" / "results" / "2099-future-w4a8"
    recs.mkdir(parents=True)
    _write_record(recs, experiment="future-exp", precision="w4a8", steps=4,
                  unet="future_q.safetensors", clip="future_te.safetensors")
    import bench.quality_gate as qg

    orig = qg.REPO
    qg.REPO = tmp_path
    try:
        d = describe_baseline(str(tmp_path / "results" / "raw" / "2099-future-w4a8"))
    finally:
        qg.REPO = orig
    assert "w4a8" in d and "4 steps" in d
    assert "bf16, 40 steps" not in d
    # the fidelity semantics note is baseline-agnostic (no bf16 assumption)
    note = SEMANTICS_NOTE["fidelity"]
    assert "bf16" not in note
    assert "specified baseline image" in note


# Case 4 — missing baseline metadata: fail closed / UNKNOWN, never guessed
def test_case4_missing_metadata_fails_closed(tmp_path):
    d = describe_baseline(tmp_path / "nowhere")
    assert "no run records found" in d
    assert "steps" not in d and "bf16" not in d  # nothing invented


# Case 5 — committed r1 artifacts: numbers, prompts, experiment ids consistent
def test_case5_committed_r1_md_and_json_agree():
    md = (R1 / "quality.md").read_text(encoding="utf-8")
    data = json.loads((R1 / "quality.json").read_text(encoding="utf-8"))
    rows = {}
    for line in md.splitlines():
        if line.startswith("| p"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows[cells[0]] = (float(cells[1]), float(cells[2]))
    assert set(rows) == {"p1-zh-scene", "p2-en-scene", "p3-poster-text"}
    assert data["experiment_name"] == "p3-turbo-int8-ck-te-nosmart-1024x1024"
    assert data["baseline_experiment"] == "p3-turbo-int8-ck-1024x1024"
    for prompt, (med, mx) in rows.items():
        assert round(data["median"][prompt], 4) == med, prompt
        assert round(data["max"][prompt], 4) == mx, prompt
    # canonical values (from the raw measurement images; never transposed)
    assert round(data["median"]["p1-zh-scene"], 4) == 0.0583
    assert round(data["max"]["p1-zh-scene"], 4) == 0.0748
    assert round(data["median"]["p2-en-scene"], 4) == 0.0115
    assert round(data["max"]["p2-en-scene"], 4) == 0.0150
    assert round(data["median"]["p3-poster-text"], 4) == 0.0137
    assert round(data["max"]["p3-poster-text"], 4) == 0.0154
    # the regenerated file no longer claims a bf16 reference for THIS gate
    semantics = next(ln for ln in md.splitlines() if "FIDELITY" in ln)
    assert "bf16 reference" not in semantics
    assert "not an absolute image-quality score" in semantics


# Case 6 — fidelity LPIPS is never presented as absolute quality
def test_case6_fidelity_note_is_not_a_quality_score():
    note = SEMANTICS_NOTE["fidelity"]
    assert "not an absolute image-quality score" in note
    assert "noise floor" in note  # calibration guidance retained
    # and the two semantics stay clearly distinct
    assert "DISTANCE, NOT QUALITY" in SEMANTICS_NOTE["distance"]
