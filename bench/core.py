"""Shared benchmark core: protocol planning, statistics, schema.

Both the diffusers harness (run_bench.py) and the ComfyUI driver
(run_comfyui.py) measure through this module so numbers are comparable.
"""

import json
from pathlib import Path

from jsonschema import validate as _validate

REPO = Path(__file__).resolve().parents[1]
PROMPTS_PATH = REPO / "bench" / "prompts.json"
SCHEMA_PATH = REPO / "bench" / "schema" / "result.schema.json"


def plan_runs(
    prompt_ids: list[str],
    resolutions: list[tuple[int, int]],
    seeds: list[int],
    warmup: int = 1,
    measured: int = 3,
) -> list[dict]:
    """Return ordered run specs: one cold first, then per config warmup+measures."""
    specs: list[dict] = []
    first = True
    for prompt_id in prompt_ids:
        for (w, h) in resolutions:
            if first:
                specs.append(
                    {"kind": "cold", "prompt_id": prompt_id, "width": w,
                     "height": h, "seed": seeds[0], "run_idx": 0}
                )
                first = False
            for _ in range(warmup):
                specs.append(
                    {"kind": "warmup", "prompt_id": prompt_id, "width": w,
                     "height": h, "seed": seeds[0], "run_idx": 0}
                )
            for i in range(measured):
                specs.append(
                    {"kind": "measure", "prompt_id": prompt_id, "width": w,
                     "height": h, "seed": seeds[i % len(seeds)], "run_idx": i}
                )
    return specs


def steady_step_rate(step_times: list[float]) -> float | None:
    """Median per-step wall time over steady steps (index 1+).

    step_times_s[0] includes text-encode + cpu-offload weight restore on top
    of step 1's compute, so it is excluded (protocol v1.1 semantics).
    """
    steady = step_times[1:]
    if not steady:
        return None
    import statistics

    return statistics.median(steady)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_record(record: dict) -> None:
    """Validate a result record against the schema; raises ValidationError."""
    _validate(record, load_schema())
