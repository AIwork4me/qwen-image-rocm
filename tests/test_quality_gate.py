"""Quality-gate tooling tests — LPIPS is mocked; only PIL runs for real."""

from pathlib import Path

import pytest
from PIL import Image

from bench import quality_gate as qg


def _touch_png(path: Path, size=(1024, 1024), color=(120, 30, 200)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def test_collect_measured_parses_prompt_seed_runidx(tmp_path):
    for name in ("p1-zh-scene-42-r0.png", "p1-zh-scene-1337-r1.png",
                 "p3-poster-text-20261030-r2.png",
                 "p1-zh-scene-1000042-cold.png", "p2-en-scene-2000042-warmup.png"):
        _touch_png(tmp_path / name)
    got = qg.collect_measured(tmp_path)
    assert set(got) == {("p1-zh-scene", 0), ("p1-zh-scene", 1), ("p3-poster-text", 2)}
    # cold/warmup files are excluded — only measured runs enter the gate


def test_make_paired_grid_layout(tmp_path):
    base_dir, exp_dir = tmp_path / "base", tmp_path / "exp"
    for rid in ("p1", "p3"):
        for idx in (0, 1, 2):
            _touch_png(base_dir / f"{rid}-42-r{idx}.png", color=(0, 0, 0))
            _touch_png(exp_dir / f"{rid}-42-r{idx}.png", color=(255, 255, 255))
    base, exp = qg.collect_measured(base_dir), qg.collect_measured(exp_dir)
    out = tmp_path / "out" / "quality_grid.png"
    n = qg.make_paired_grid(base, exp, out, tile=64)
    assert n == 6
    img = Image.open(out)
    # 2 prompts (rows) x 3 seeds x [base|exp] (6 cols) at 64px
    assert img.size == (6 * 64, 2 * (64 + 20))


def test_make_native_crops_native_resolution(tmp_path):
    b = _touch_png(tmp_path / "b.png")
    e = _touch_png(tmp_path / "e.png", color=(10, 10, 10))
    out = tmp_path / "out" / "crops.png"
    qg.make_native_crops(b, e, out, crop=512)
    img = Image.open(out)
    assert img.size == (2 * 512, 2 * (512 + 20))  # no downscale: 1:1 pasted crops


def test_lpips_table_per_prompt_medians(tmp_path, monkeypatch):
    calls = []

    def fake_lpips(a, b):
        calls.append((a.name, b.name))
        # poster gets systematically larger distance than scenes
        return 0.40 if "poster" in a.name else 0.02 + 0.01 * len(calls)

    monkeypatch.setattr(qg, "_lpips_pair_impl", fake_lpips)
    base_dir, exp_dir = tmp_path / "b", tmp_path / "e"
    for name in ("p1-scene", "p3-poster"):
        for idx in (0, 1, 2):
            _touch_png(base_dir / f"{name}-42-r{idx}.png")
            _touch_png(exp_dir / f"{name}-42-r{idx}.png")
    table = qg.lpips_table(qg.collect_measured(base_dir), qg.collect_measured(exp_dir))
    assert set(table) == {"p1-scene", "p3-poster"}
    assert table["p1-scene"]["n"] == 3 and table["p3-poster"]["n"] == 3
    assert table["p3-poster"]["median"] > table["p1-scene"]["median"]
    assert len(calls) == 6


@pytest.mark.parametrize("semantics", ["fidelity", "distance"])
def test_quality_md_semantics_and_verdict(tmp_path, semantics):
    table = {"p1": {"median": 0.05, "max": 0.07, "n": 3, "scores": [0.05, 0.07]}}
    out = tmp_path / "quality.md"
    qg.write_quality_md(out, "p3-x", semantics, table, 0.012, "base/", "exp/")
    text = out.read_text(encoding="utf-8")
    assert "p3-x" in text
    assert ("DISTANCE, NOT QUALITY" in text) == (semantics == "distance")
    assert ("FIDELITY" in text) == (semantics == "fidelity")
    assert "0.0120" in text  # noise floor printed
    for tier in ("无感", "略降", "不可接受"):  # three-tier user verdict slots
        assert tier in text
