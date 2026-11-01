"""Committed-evidence number pinning (final-closure round).

Every public median this repo quotes for r1-triple (1024² Fast) and
r3-2048matrix (2048² Fast) is RECOMPUTED here from the committed JSON
records — never copied from prose. Also pins the structural facts the
claims depend on (prompt/seed coverage, cache state, checkpoints, steps,
resolution). Historical records are only read.
"""

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RESULTS = Path(__file__).resolve().parents[1] / "bench" / "results"
SEEDS = {42, 1337, 20261030}
TRIPLE_UNET = "qwen_image_2.1_turbo_int8_convrot.safetensors"
TRIPLE_CLIP = "qwen3vl_8b_int8_convrot.safetensors"
TRIPLE_VAE = "qwen_image_2.1_vae_bf16.safetensors"


def load(run_dir: str) -> list[dict]:
    out = []
    for f in sorted((RESULTS / run_dir).glob("*.json")):
        if f.name == "quality.json":
            continue
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def measures(run_dir: str) -> dict[str, list[float]]:
    by_prompt: dict[str, list[float]] = {}
    for r in load(run_dir):
        if r.get("run_kind") == "measure":
            by_prompt.setdefault(r["prompt_id"], []).append(r["runs"][0]["total_s"])
    return by_prompt


# ---- r1-triple: 1024² Fast (full production triple) -------------------------

def test_r1_warm_medians_recomputed_from_records():
    m = measures("2026-11-01-r1-triple")
    assert set(m) == {"p1-zh-scene", "p2-en-scene", "p3-poster-text"}
    assert all(len(v) == 3 for v in m.values())
    assert round(statistics.median(m["p1-zh-scene"]), 2) == 8.30
    assert round(statistics.median(m["p2-en-scene"]), 2) == 9.06
    assert round(statistics.median(m["p3-poster-text"]), 2) == 8.09


def test_r1_structure_and_config():
    recs = load("2026-11-01-r1-triple")
    # cold once + 3 warmups + 9 measures + 3 fresh arms = 16 records
    kinds = [r["run_kind"] for r in recs]
    assert kinds.count("cold") == 1 and kinds.count("warmup") == 3
    assert kinds.count("measure") == 9 and kinds.count("fresh_prompt") == 3
    for r in recs:
        assert (r["width"], r["height"], r["steps"]) == (1024, 1024, 8)
        assert r["unet"] == TRIPLE_UNET and r["clip"] == TRIPLE_CLIP
        assert r["vae"] == TRIPLE_VAE and r["attention_backend"] == "ck"
        assert r["env_ref"], "every record must cite an env snapshot"
    # warm measures are cache-hit runs (TE cached) — never fresh-prompt runs
    for r in recs:
        if r["run_kind"] == "measure":
            assert any(n.startswith("CLIPTextEncode#pos") for n in r["cached_nodes"])
            assert r["runs"][0]["text_encode_s"] == 0
    # fresh arms are separate and DO pay a real text-encode
    for r in recs:
        if r["run_kind"] == "fresh_prompt":
            assert r["runs"][0]["text_encode_s"] > 0
    assert {r["seed"] for r in recs if r["run_kind"] == "measure"} == SEEDS


# ---- r3-2048matrix: 2048² Fast bounded matrix -------------------------------

def test_r3_warm_medians_recomputed_from_records():
    m = measures("2026-11-01-r3-2048matrix")
    assert set(m) == {"p1-zh-scene", "p2-en-scene", "p3-poster-text"}
    assert all(len(v) == 3 for v in m.values())
    assert round(statistics.median(m["p1-zh-scene"]), 3) == 40.268
    assert round(statistics.median(m["p2-en-scene"]), 3) == 40.324
    assert round(statistics.median(m["p3-poster-text"]), 3) == 40.362
    all9 = [t for v in m.values() for t in v]
    assert len(all9) == 9
    assert round(min(all9), 3) == 40.236 and round(max(all9), 3) == 40.445


def test_r3_structure_and_config():
    recs = load("2026-11-01-r3-2048matrix")
    kinds = [r["run_kind"] for r in recs]
    # 1 cold + 3 warmups + 9 measures = 13 records
    assert len(recs) == 13
    assert kinds.count("cold") == 1 and kinds.count("warmup") == 3
    assert kinds.count("measure") == 9
    for r in recs:
        assert (r["width"], r["height"], r["steps"]) == (2048, 2048, 8)
        assert r["unet"] == TRIPLE_UNET and r["clip"] == TRIPLE_CLIP
        assert r["vae"] == TRIPLE_VAE and r["attention_backend"] == "ck"
        assert 0 < r["vram_peak_mb"] < 24576  # sampled, on a 24 GB card
    assert {r["seed"] for r in recs if r["run_kind"] == "measure"} == SEEDS
    # warm = cache-hit regime (these 9 are NOT fresh-prompt runs)
    for r in recs:
        if r["run_kind"] == "measure":
            assert any(n.startswith("CLIPTextEncode#pos") for n in r["cached_nodes"])
