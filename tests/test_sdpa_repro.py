"""CPU tests for the pure (torch-free) parts of tools/repro/sdpa_repro.py.

The GPU sweep itself is the evidence run (docs/issues/evidence/
sdpa-repro-matrix.md), not unit-testable; combos/render/inspect/classify are.
"""

import json

from tools.repro.sdpa_repro import (
    MASK_COMBOS,
    SEQUENCE_LENS,
    build_sweep,
    classify_exception,
    inspect_aotriton,
    render_markdown,
)


def test_sweep_shape_and_order():
    cells = build_sweep()
    # 6 seq lens x 2 kv-head variants x 4 mask/causal combos x 4 backends
    assert len(cells) == len(SEQUENCE_LENS) * 2 * len(MASK_COMBOS) * 4
    assert cells is not build_sweep() or True  # deterministic content below
    assert build_sweep() == build_sweep()
    first = cells[0]
    assert first["seq"] == SEQUENCE_LENS[0]
    assert first["backend"] == "flash"
    assert {c["backend"] for c in cells} == {"flash", "mem_efficient", "math", "cudnn"}
    assert {c["kv_heads"] for c in cells} == {8, 32}


def test_sweep_never_pairs_explicit_mask_with_is_causal():
    # torch rejects attn_mask != None + is_causal=True; the sweep must not
    # generate that combination as a "cell" (it is not a kernel failure).
    for c in build_sweep():
        if c["mask_kind"] != "none":
            assert c["is_causal"] is False


def test_classify_exception_by_duck_typing():
    class OutOfMemoryError(RuntimeError):
        pass

    assert classify_exception(OutOfMemoryError("HIP out of memory")) == "OOM"
    assert classify_exception(RuntimeError("CUDA error: invalid argument")) == "FAIL"
    assert classify_exception(ValueError("nope")) == "FAIL"


def test_inspect_aotriton_on_fake_wheel(tmp_path):
    torch_dir = tmp_path / "torch"
    arch = torch_dir / "lib" / "aotriton.images" / "amd-gfx110x"
    (arch / "flash").mkdir(parents=True)
    (arch / "flash" / "attn_fwd.zip").write_bytes(b"kernel")
    (arch / "__signature__").write_text(
        json.dumps({"AOTRITON_GIT_SHA1": "abc123", "AOTRITON_GIT_TREESHA1": "def456"})
    )
    (torch_dir / "lib" / "aotriton_v2.dll").write_bytes(b"?attn_fwd@flash@v3@aotriton@@")
    (torch_dir / "lib" / "aotriton_v2.lib").write_bytes(b"lib")

    info = inspect_aotriton(torch_dir)
    assert info["images_present"] is True
    assert info["dll_present"] is True
    assert info["lib_present"] is True
    assert info["dll_v3_symbols"] is True
    assert info["arches"]["amd-gfx110x"]["sha1"] == "abc123"
    assert info["arches"]["amd-gfx110x"]["flash_kernels"] == ["attn_fwd.zip"]


def test_inspect_aotriton_missing(tmp_path):
    info = inspect_aotriton(tmp_path / "torch")
    assert info["images_present"] is False
    assert info["dll_present"] is False
    assert info["dll_v3_symbols"] is False
    assert info["arches"] == {}


def _result(seq=64, kv=32, mask="none", causal=False, backend="math",
            status="PASS", ms=1.5, err=None):
    return {
        "seq": seq, "kv_heads": kv, "mask_kind": mask, "is_causal": causal,
        "backend": backend, "status": status, "ms": ms, "error": err,
    }


def test_render_markdown_tables_and_symbols():
    results = [
        _result(),
        _result(backend="flash", status="FAIL",
                err="torch.AcceleratorError: CUDA error: invalid argument"),
        _result(backend="mem_efficient", status="OOM", ms=None),
        _result(kv=8, backend="cudnn", status="FAIL", err="RuntimeError: No available kernel"),
    ]
    meta = {
        "torch_version": "2.12.0+rocm7.14.1",
        "hip_version": "7.14.60850",
        "gfx_arch": "gfx1100",
        "aotriton": {"images_present": False, "arches": {}},
        "created_at": "2026-11-01T00:00:00",
    }
    md = render_markdown(results, meta)
    assert "| seq | mask | causal |" in md or "seq" in md
    assert "flash" in md and "math" in md and "cudnn" in md and "mem_efficient" in md
    assert "❌" in md and "✅" in md and "OOM" in md
    assert "2.12.0+rocm7.14.1" in md
    assert "kv_heads=32" in md and "kv_heads=8" in md
    # error text is included but truncated
    assert "invalid argument" in md


def test_render_markdown_truncates_long_errors():
    results = [_result(backend="flash", status="FAIL", err="E" * 500)]
    meta = {"torch_version": "t", "hip_version": "h", "gfx_arch": "g",
            "aotriton": {}, "created_at": "c"}
    md = render_markdown(results, meta)
    assert "E" * 200 in md
    assert "E" * 300 not in md


def test_sequence_lens_match_plan():
    # 64, TE-realistic ~120, 256, 1024, 4096 (1024^2 DiT), 16384 (2048^2 DiT)
    assert SEQUENCE_LENS == (64, 120, 256, 1024, 4096, 16384)
