import json

import pytest
from jsonschema import validate

SCHEMA = json.loads(open("bench/schema/result.schema.json", encoding="utf-8").read())


def _manifest():
    from bench.experiments import load_manifest

    m = load_manifest("p2-comfyui-1024x1024")
    m["experiment_name"] = m["name"]
    return m


def _summary():
    return {
        "text_encode_s": 0.0,
        "vae_decode_s": 2.0,
        "ksampler_s": 100.0,
        "step_times_s": [1.2, 1.1],
        "node_timings_s": {"KSampler#ks": 100.0},
        "cached_nodes": ["CLIPTextEncode#pos"],
        "vram_peak_mb": 17000.0,
        "vram_residency_mb": 16500.0,
        "monitor_error": None,
    }


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
        _manifest(), _spec(),
        total_s=123.4, execution_time_s=110.0, summary=_summary(),
        env_ref="snapshot-x.json", session_id="sess-a", restart_idx=1,
    )
    validate(rec, SCHEMA)  # schema-valid including required fields
    assert rec["framework"] == "comfyui"
    assert rec["phase"] == 2
    assert rec["experiment"] == "p2-comfyui-1024x1024"
    assert rec["run_kind"] == "measure"
    assert rec["attention_backend"] == "comfyui-default"
    assert rec["sampler"] == "euler"
    assert rec["scheduler"] == "simple"
    assert rec["cfg"] == 1.0  # recorded since v1.3 (was hardcoded before)
    assert rec["steps"] == 40
    assert rec["execution_time_s"] == 110.0
    assert rec["runs"][0]["denoise_s"] == 110.0  # documented approximation (continuity)
    assert rec["runs"][0]["step_times_s"] == [1.2, 1.1]  # ws per-step timing
    assert rec["runs"][0]["text_encode_s"] == 0.0  # cache hit on measured runs
    assert rec["ksampler_s"] == 100.0  # true denoise from node timing
    assert rec["vram_peak_mb"] == 17000.0  # sampled peak
    assert rec["vram_residency_mb"] == 16500.0  # old post-run metric kept
    assert rec["session_id"] == "sess-a"
    assert rec["restart_idx"] == 1
    assert rec["cached_nodes"] == ["CLIPTextEncode#pos"]
    assert "monitor_error" not in rec


def test_result_record_cold_and_fresh_kinds():
    from bench.run_comfyui import build_record

    rec_cold = build_record(
        _manifest(), _spec("cold"), total_s=200.0, execution_time_s=180.0,
        summary=_summary(), env_ref="s.json", session_id="s", restart_idx=0,
    )
    assert rec_cold["runs"][0]["kind"] == "cold"

    rec_fresh = build_record(
        _manifest(), _spec("fresh_prompt"), total_s=80.0, execution_time_s=70.0,
        summary=_summary(), env_ref="s.json", session_id="s", restart_idx=0,
    )
    validate(rec_fresh, SCHEMA)
    assert rec_fresh["runs"][0]["kind"] == "fresh"
    assert rec_fresh["run_kind"] == "fresh_prompt"


def test_monitor_error_recorded():
    from bench.run_comfyui import build_record

    s = dict(_summary(), monitor_error="ws connect failed: x")
    rec = build_record(
        _manifest(), _spec(), total_s=50.0, execution_time_s=45.0, summary=s,
        env_ref="s.json", session_id="s", restart_idx=0,
    )
    assert rec["monitor_error"].startswith("ws connect")


def test_sequential_queue_order():
    from bench.core import plan_runs
    from bench.run_comfyui import order_specs

    specs = plan_runs(["a", "b", "c"], [(1024, 1024)], [42, 1337, 20261030])
    # driver executes exactly the plan order, one at a time (no batching)
    assert order_specs(specs) == specs
    with pytest.raises(ValueError):
        order_specs([])  # empty plan is a caller bug
