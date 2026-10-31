import pytest
from jsonschema import ValidationError


def test_core_exports():
    from bench import core

    specs = core.plan_runs(["a"], [(1024, 1024)], [42])
    kinds = [s["kind"] for s in specs]
    # one config: cold (process-first) + 1 warmup + 3 measured runs
    assert kinds == ["cold", "warmup", "measure", "measure", "measure"]
    # cold/warmup use a bumped seed so ComfyUI's execution cache can never
    # serve a cached result to a measured run (warm seed collision found in
    # phase 2; protocol v1.2)
    assert specs[0]["seed"] == 1_000_042
    assert specs[1]["seed"] == 1_000_042
    assert [s["seed"] for s in specs[2:]] == [42, 42, 42]
    assert core.steady_step_rate([12.0, 1.0, 1.0]) == 1.0
    assert isinstance(core.load_schema(), dict)
    assert core.PROMPTS_PATH.name == "prompts.json"
    assert core.REPO.name == "image"


def test_validate_record_rejects_bad():
    from bench.core import validate_record

    with pytest.raises(ValidationError):
        validate_record({"experiment": "x"})  # missing required fields


def test_validate_record_accepts_valid():
    from bench.core import validate_record

    validate_record(
        {
            "experiment": "p2-comfyui-1024x1024",
            "phase": 2,
            "framework": "comfyui",
            "precision": "bf16",
            "width": 1024,
            "height": 1024,
            "steps": 40,
            "seed": 42,
            "prompt_id": "p1-zh-scene",
            "protocol_version": "v1",
            "runs": [
                {
                    "kind": "warm",
                    "total_s": 60.0,
                    "text_encode_s": None,
                    "denoise_s": 55.0,
                    "vae_decode_s": None,
                    "step_times_s": [],
                }
            ],
            "vram_peak_mb": 20000.0,
            "env_ref": "snapshot-test.json",
            "created_at": "2026-10-31T10:00:00+08:00",
            "run_kind": "measure",
            "attention_backend": "comfyui-default",
            "sampler": "euler",
            "scheduler": "simple",
        }
    )
