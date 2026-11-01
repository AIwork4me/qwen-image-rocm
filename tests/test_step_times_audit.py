"""Unit tests for the step-times completeness audit (P1-9) + the corpus
inventory fact established 2026-11-01: monitor-era warmup/fresh/cold records
frequently carry one fewer step event (the step-1 event is lost at monitor
connect), and some cold records have none. Totals and node timings are
server-side and unaffected; no published number derives from step_times_s.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_step_times import classify  # noqa: E402


def rec(proto, steps, samples):
    return {"protocol_version": proto, "steps": steps,
            "runs": [{"step_times_s": samples}]}


def test_monitor_era_exact_match_is_complete():
    assert classify(rec("v1.3", 8, [0.5] * 8)) == "complete"
    assert classify(rec("v1.3", 40, [0.5] * 40)) == "complete"


def test_monitor_era_short_or_empty_is_incomplete():
    assert classify(rec("v1.3", 8, [0.5] * 7)) == "incomplete"   # lost step-1
    assert classify(rec("v1.3", 40, [])) == "incomplete"         # cold, no events
    assert classify(rec("v1.3", 40, [0.5] * 39)) == "incomplete"


def test_pre_monitor_eras_are_monitor_absent_not_defects():
    assert classify(rec("v1", 40, [])) == "monitor-absent"
    assert classify(rec("v1.1", 40, [])) == "monitor-absent"
    assert classify(rec("v1.2", 40, [0.5] * 3)) == "monitor-absent"


def test_malformed_is_na():
    assert classify({"protocol_version": "v1.3"}) == "n/a"
    assert classify({"protocol_version": "v1.3", "steps": 8, "runs": [{}]}) == "n/a"


def test_corpus_scan_tool_runs_and_reports_inventory():
    import subprocess

    proc = subprocess.run(
        [sys.executable, "-I", str(Path(__file__).resolve().parents[1]
                                   / "tools" / "check_step_times.py")],
        capture_output=True, text=True, timeout=120,
    )
    out = proc.stdout
    # committed corpus fact (2026-11-01): incomplete records exist and are
    # inventoried; if this number drifts, a NEW run wrote partial step data —
    # investigate before shipping docs that quote per-step numbers
    assert "records scanned" in out and "INCOMPLETE" in out
    assert "samples=" in out
