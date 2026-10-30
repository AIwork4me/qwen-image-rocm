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
        "steps": 4,
        "seed": 42,
        "prompt_id": "p1-zh-scene",
        "protocol_version": "v1",
        "runs": [
            {
                "kind": "warm",
                "total_s": 60.0,
                "text_encode_s": None,
                "denoise_s": 43.0,
                "vae_decode_s": None,
                # step 1 carries text-encode + offload restore (12.0s);
                # steady steps are 1.0s each
                "step_times_s": [12.0, 1.0, 1.0, 1.0],
            }
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
    # steady-state s/step excludes step 1 (text-encode + offload tax):
    # median of [1.0, 1.0, 1.0] = 1.00, NOT denoise_s/steps = 10.75
    assert "| 1.00 |" in report
    # step-1 semantics must be disclosed, not claimed pure
    assert "step_times_s[0]" in report


def test_steady_step_rate_ignores_first_step():
    from bench.make_report import steady_step_rate

    assert steady_step_rate([12.0, 1.0, 1.0, 1.0]) == 1.0
    assert steady_step_rate([5.0]) is None  # single step: no steady state
