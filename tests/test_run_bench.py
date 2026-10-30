import json


def test_cold_emitted_once():
    from bench.run_bench import plan_runs

    specs = plan_runs(
        prompt_ids=["p1-zh-scene", "p2-en-scene", "p3-poster-text"],
        resolutions=[(1024, 1024), (2048, 2048)],
        seeds=[42, 1337, 20261030],
    )
    kinds = [s["kind"] for s in specs]
    assert kinds.count("cold") == 1
    assert kinds.count("warmup") == 6  # one per config (prompt x resolution)
    assert kinds.count("measure") == 18  # 3 seeds per config


def test_matrix_covers_all_combos():
    from bench.run_bench import plan_runs

    prompt_ids = ["p1-zh-scene", "p2-en-scene", "p3-poster-text"]
    resolutions = [(1024, 1024), (2048, 2048)]
    seeds = [42, 1337, 20261030]
    specs = plan_runs(prompt_ids=prompt_ids, resolutions=resolutions, seeds=seeds)
    measure = [s for s in specs if s["kind"] == "measure"]
    combos = {(s["prompt_id"], s["width"], s["height"], s["seed"]) for s in measure}
    expected = {
        (p, w, h, seed) for p in prompt_ids for (w, h) in resolutions for seed in seeds
    }
    assert combos == expected
    # cold comes first, warmup precedes its config's measures
    assert specs[0]["kind"] == "cold"


def test_make_report_smoke(tmp_path):
    from bench.make_report import make_report

    sample = {
        "experiment": "p1-bf16-1024x1024",
        "phase": 1,
        "framework": "diffusers",
        "precision": "bf16",
        "width": 1024,
        "height": 1024,
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
                "total_s": 60.0,
                "text_encode_s": None,
                "denoise_s": 50.0,
                "vae_decode_s": None,
                "step_times_s": [1.25] * 40,
            },
            {
                "kind": "warm",
                "total_s": 62.0,
                "text_encode_s": None,
                "denoise_s": 51.0,
                "vae_decode_s": None,
                "step_times_s": [1.28] * 40,
            },
            {
                "kind": "warm",
                "total_s": 64.0,
                "text_encode_s": None,
                "denoise_s": 52.0,
                "vae_decode_s": None,
                "step_times_s": [1.3] * 40,
            },
        ],
        "vram_peak_mb": 21000.0,
        "env_ref": "snapshot-test.json",
        "created_at": "2026-10-30T22:00:00+08:00",
        "run_kind": "measure",
    }
    d = tmp_path / "results"
    d.mkdir()
    (d / "sample1.json").write_text(json.dumps(sample), encoding="utf-8")
    s2 = dict(sample, seed=1337)
    (d / "sample2.json").write_text(json.dumps(s2), encoding="utf-8")

    make_report(str(d))
    report = (d / "report.md").read_text(encoding="utf-8")
    assert "p1-bf16-1024x1024" in report
    assert "median" in report.lower()
    assert "limitations" in report.lower()
