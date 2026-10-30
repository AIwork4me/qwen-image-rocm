import json

import pytest
from jsonschema import ValidationError, validate

SCHEMA_PATH = "bench/schema/result.schema.json"


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


GOOD_SAMPLE = {
    "experiment": "p1-bf16-2048x2048",
    "phase": 1,
    "framework": "diffusers",
    "precision": "bf16",
    "width": 2048,
    "height": 2048,
    "steps": 40,
    "seed": 42,
    "prompt_id": "p1-zh-scene",
    "protocol_version": "v1",
    "runs": [
        {
            "kind": "cold",
            "total_s": 120.5,
            "text_encode_s": None,
            "denoise_s": 100.2,
            "vae_decode_s": None,
            "step_times_s": [2.5] * 40,
        },
        {
            "kind": "warm",
            "total_s": 60.1,
            "text_encode_s": 3.2,
            "denoise_s": 50.0,
            "vae_decode_s": 6.9,
            "step_times_s": [1.25] * 40,
        },
    ],
    "vram_peak_mb": 21000.0,
    "env_ref": "snapshot-20261030.json",
    "created_at": "2026-10-30T20:00:00+08:00",
}


def test_schema_validates_good_sample():
    validate(GOOD_SAMPLE, load_schema())


def test_schema_rejects_missing_seed():
    bad = dict(GOOD_SAMPLE)
    del bad["seed"]
    with pytest.raises(ValidationError):
        validate(bad, load_schema())


def test_schema_run_kind_enum():
    schema = load_schema()
    good = dict(GOOD_SAMPLE, run_kind="measure")
    validate(good, schema)
    bad = dict(GOOD_SAMPLE, run_kind="measures")
    with pytest.raises(ValidationError):
        validate(bad, schema)
