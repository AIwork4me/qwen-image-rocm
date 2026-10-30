import json

import pytest
from jsonschema import validate

SCHEMA = json.loads(open("bench/schema/result.schema.json", encoding="utf-8").read())


def _spec(kind="measure"):
    return {
        "kind": kind,
        "prompt_id": "p1-zh-scene",
        "width": 1024,
        "height": 1024,
        "seed": 42,
        "run_idx": 0,
    }


def test_result_record_fields():
    from bench.run_comfyui import build_record

    rec = build_record(
        _spec(),
        total_s=123.4,
        execution_time_s=110.0,
        vram_peak_mb=19000.0,
        env_ref="snapshot-x.json",
    )
    validate(rec, SCHEMA)  # schema-valid including required fields
    assert rec["framework"] == "comfyui"
    assert rec["phase"] == 2
    assert rec["experiment"] == "p2-comfyui-1024x1024"
    assert rec["run_kind"] == "measure"
    assert rec["attention_backend"] == "comfyui-default"
    assert rec["sampler"] == "euler"
    assert rec["scheduler"] == "simple"
    assert rec["execution_time_s"] == 110.0
    assert rec["runs"][0]["denoise_s"] == 110.0  # documented approximation
    assert rec["runs"][0]["step_times_s"] == []
    assert rec["runs"][0]["kind"] == "warm"


def test_result_record_cold_kind():
    from bench.run_comfyui import build_record

    rec = build_record(
        _spec("cold"), total_s=200.0, execution_time_s=180.0,
        vram_peak_mb=19000.0, env_ref="s.json",
    )
    assert rec["runs"][0]["kind"] == "cold"


def test_sequential_queue_order():
    from bench.core import plan_runs
    from bench.run_comfyui import order_specs

    specs = plan_runs(["a", "b", "c"], [(1024, 1024)], [42, 1337, 20261030])
    # driver executes exactly the plan order, one at a time (no batching)
    assert order_specs(specs) == specs
    with pytest.raises(ValueError):
        order_specs([])  # empty plan is a caller bug
