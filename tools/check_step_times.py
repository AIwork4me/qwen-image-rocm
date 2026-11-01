"""Step-time completeness audit over the run-record corpus (review P1-9).

For every record produced under protocol v1.3 (the websocket-monitor era),
``len(runs[0].step_times_s)`` must equal the manifest's ``steps``. A monitor
that dropped websocket events would show fewer samples — such a record must
be flagged INCOMPLETE and its per-step numbers treated as partial evidence,
never back-filled or averaged as if whole.

Eras before v1.3 (phase-1 diffusers reports, phase-2 API-only ComfyUI runs)
had no per-step monitor at all: empty lists there are MONITOR-ABSENT
(expected), not a defect. This tool never modifies records; it reports.

Usage:  python -I tools/check_step_times.py [bench/results]
Exit 0 unless incomplete records are found in monitor-era records (then 1).
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# protocol v1.3 = first version with the websocket step monitor
MONITOR_PROTOCOLS = {"v1.3"}
# experiments known to be ComfyUI-API-era (no step events) even in v1.3 dir names
API_ERA_HINTS = ("2026-10-31",)


def classify(record: dict) -> str:
    """complete | incomplete | monitor-absent | n/a"""
    proto = record.get("protocol_version", "")
    steps = record.get("steps")
    samples = record.get("runs", [{}])[0].get("step_times_s", None)
    if samples is None or steps is None:
        return "n/a"
    if proto in MONITOR_PROTOCOLS:
        return "complete" if len(samples) == steps else "incomplete"
    return "monitor-absent"  # pre-monitor era: empty/short lists are expected


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "bench" / "results"
    stats: dict[str, int] = {}
    incomplete: list[tuple[str, int, int]] = []  # (file, steps, samples)
    files = sorted(
        p for p in root.rglob("*.json")
        if p.name not in {"quality.json"} and "raw" not in p.parts
    )
    for f in files:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict) or "runs" not in rec:
            continue  # non-record json (env snapshots, manifests...)
        kind = classify(rec)
        stats[kind] = stats.get(kind, 0) + 1
        if kind == "incomplete":
            samples = rec["runs"][0]["step_times_s"]
            incomplete.append((str(f.relative_to(root)), rec["steps"], len(samples)))
    print(f"records scanned under {root}: {sum(stats.values())}")
    for kind in ("complete", "incomplete", "monitor-absent", "n/a"):
        if stats.get(kind):
            print(f"  {kind:16s} {stats[kind]}")
    if incomplete:
        print("INCOMPLETE step-monitor records (do NOT quote per-step numbers from these):")
        for path, steps, n in incomplete:
            print(f"  {path}: steps={steps} samples={n}")
        return 1
    print("no incomplete monitor-era records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
