"""Minimal SDPA repro: hipErrorInvalidValue from flash/mem-efficient backends.

Sweeps the attention shapes used by Qwen-Image-2.1 (DiT: 32Q/32KV heads,
S~4096@1024² / ~16384@2048²; text encoder: GQA 32Q/8KV, causal, short S)
across SDPA backends, masks, and sequence lengths — no model weights needed.

Deps: torch only (plus stdlib), so the same script runs unchanged in the
phase1 baseline venv and in bare phase4 diagnostic venvs.

Error flushing follows ComfyUI's probe pattern (comfy/model_management.py
``aotriton_supported``): launch -> torch.cuda.synchronize() -> a tiny dummy
add whose ``.item()`` raises the async launch error, so a kernel that fails
silently at launch is turned into a catchable exception per cell.

Also inspects the installed torch wheel's AOTriton artifacts (images
``__signature__`` git SHA + runtime DLL symbols) — the mismatch family from
TheRock#7315/#7992: runtime library pinned to one AOTriton commit while
``aotriton.images`` ships kernels from another.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# --- sweep definition (pure data; mirrors Annex B of the Phase 4 plan) ------

SEQUENCE_LENS = (64, 120, 256, 1024, 4096, 16384)  # 120 = TE-realistic prompt
Q_HEADS = 32
HEAD_DIM = 128
KV_HEADS = (32, 8)  # 32 = DiT full attention, 8 = Qwen3-VL GQA
BACKENDS = ("flash", "mem_efficient", "math", "cudnn")
# (mask_kind, is_causal); torch rejects explicit mask + is_causal=True, so
# that pair is never generated — it is an API error, not a kernel failure.
MASK_COMBOS = (("none", False), ("none", True), ("bool4d", False), ("float_add", False))

ERROR_TRUNC = 200


def build_sweep(
    seq_lens: tuple[int, ...] = SEQUENCE_LENS,
    kv_heads: tuple[int, ...] = KV_HEADS,
    backends: tuple[str, ...] = BACKENDS,
) -> list[dict]:
    """Deterministic cell list: ordered by seq, kv_heads, mask combo, backend."""
    cells = []
    for seq in seq_lens:
        for kv in kv_heads:
            for mask_kind, is_causal in MASK_COMBOS:
                for backend in backends:
                    cells.append(
                        {
                            "seq": seq,
                            "kv_heads": kv,
                            "mask_kind": mask_kind,
                            "is_causal": is_causal,
                            "backend": backend,
                        }
                    )
    return cells


def classify_exception(exc: Exception) -> str:
    """OOM vs FAIL by duck typing so the classifier stays torch-import-free."""
    if type(exc).__name__ == "OutOfMemoryError" or "out of memory" in str(exc).lower():
        return "OOM"
    return "FAIL"


# --- AOTriton wheel inspection (pure; filesystem only) ----------------------


def inspect_aotriton(torch_dir: Path) -> dict:
    """Evidence from the installed wheel: images signature SHA + DLL symbols."""
    torch_dir = Path(torch_dir)
    lib = torch_dir / "lib"
    images = lib / "aotriton.images"
    arches: dict[str, dict] = {}
    if images.is_dir():
        for arch_dir in sorted(p for p in images.iterdir() if p.is_dir()):
            info: dict = {"sha1": None, "flash_kernels": []}
            sig = arch_dir / "__signature__"
            if sig.is_file():
                try:
                    info["sha1"] = json.loads(sig.read_text()).get("AOTRITON_GIT_SHA1")
                except (OSError, ValueError):
                    pass
            flash_dir = arch_dir / "flash"
            if flash_dir.is_dir():
                info["flash_kernels"] = sorted(p.name for p in flash_dir.iterdir())
            arches[arch_dir.name] = info
    dll = lib / "aotriton_v2.dll"
    dll_v3 = False
    if dll.is_file():
        try:
            dll_v3 = b"@v3@aotriton" in dll.read_bytes()
        except OSError:
            dll_v3 = False
    return {
        "images_present": bool(arches),
        "arches": arches,
        "dll_present": dll.is_file(),
        "lib_present": (lib / "aotriton_v2.lib").is_file(),
        "dll_v3_symbols": dll_v3,
    }


# --- GPU sweep (torch imported lazily; requires a CUDA/HIP device) ----------


def _make_inputs(cell: dict, torch, device, dtype):
    seq, kv = cell["seq"], cell["kv_heads"]
    q = torch.randn(1, Q_HEADS, seq, HEAD_DIM, dtype=dtype, device=device)
    k = torch.randn(1, kv, seq, HEAD_DIM, dtype=dtype, device=device)
    v = torch.randn(1, kv, seq, HEAD_DIM, dtype=dtype, device=device)
    mask = None
    if cell["mask_kind"] == "bool4d":
        m = torch.ones(seq, seq, dtype=torch.bool, device=device).tril()
        mask = m[None, None, :, :]
    elif cell["mask_kind"] == "float_add":
        m = torch.zeros(seq, seq, dtype=dtype, device=device)
        m.masked_fill_(~torch.ones(seq, seq, dtype=torch.bool, device=device).tril(), float("-inf"))
        mask = m[None, None, :, :]
    return q, k, v, mask


def run_cell(cell: dict, device: str = "cuda", warmup: int = 1, reps: int = 3) -> dict:
    """One sweep cell; returns {**cell, status, ms, error}."""
    import torch
    import torch.nn.functional as F
    from torch.nn.attention import SDPBackend, sdpa_kernel

    backend_map = {
        "flash": SDPBackend.FLASH_ATTENTION,
        "mem_efficient": SDPBackend.EFFICIENT_ATTENTION,
        "math": SDPBackend.MATH,
        "cudnn": SDPBackend.CUDNN_ATTENTION,
    }
    dtype = torch.bfloat16
    try:
        q, k, v, mask = _make_inputs(cell, torch, device, dtype)
    except Exception as exc:  # e.g. mask build OOM at S=16384
        return {**cell, "status": classify_exception(exc), "ms": None,
                "error": " ".join(str(exc).split())[:ERROR_TRUNC]}
    kwargs = {
        "attn_mask": mask,
        "is_causal": cell["is_causal"],
        "enable_gqa": cell["kv_heads"] != Q_HEADS,
    }

    def call(q=q, k=k, v=v, kwargs=kwargs):
        return F.scaled_dot_product_attention(q, k, v, **kwargs)

    try:
        with sdpa_kernel(backend_map[cell["backend"]]):
            for _ in range(warmup):
                call()
            _flush(torch, device)  # ComfyUI-style: surface async launch errors
            times = []
            for _ in range(reps):
                t0 = time.perf_counter()
                call()
                torch.cuda.synchronize()
                times.append((time.perf_counter() - t0) * 1000.0)
        _flush(torch, device)
        ms = round(statistics.median(times), 3)
        return {**cell, "status": "PASS", "ms": ms, "error": None}
    except Exception as exc:
        try:
            torch.cuda.synchronize()  # drain pending async error for next cells
        except Exception:
            pass
        return {**cell, "status": classify_exception(exc), "ms": None,
                "error": " ".join(str(exc).split())[:ERROR_TRUNC]}
    finally:
        del q, k, v, mask
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _flush(torch, device: str) -> None:
    """model_management.py pattern: sync + dummy add whose .item() raises."""
    torch.cuda.synchronize()
    torch.zeros(1, device=device).add_(1).item()


# --- rendering --------------------------------------------------------------


def _cell_text(r: dict) -> str:
    if not r:
        return "—"
    if r["status"] == "PASS":
        return f"✅ {r['ms']:.2f}ms"
    if r["status"] == "OOM":
        return "❌ OOM"
    return f"❌ {(r.get('error') or '?')[:ERROR_TRUNC]}"


def render_markdown(results: list[dict], meta: dict) -> str:
    lines = [
        "# SDPA repro matrix",
        "",
        f"- created: {meta.get('created_at')}",
        f"- torch: {meta.get('torch_version')} (git {meta.get('torch_git_version')})",
        f"- HIP: {meta.get('hip_version')} | arch: {meta.get('gfx_arch')} |"
        f" device: {meta.get('device_name')}",
    ]
    aot = meta.get("aotriton") or {}
    if aot.get("images_present"):
        shas = {a["sha1"] for a in aot["arches"].values() if a.get("sha1")}
        lines.append(
            f"- aotriton.images: {sorted(aot['arches'])} sha1={sorted(shas)};"
            f" aotriton_v2.dll v3-symbols={aot.get('dll_v3_symbols')}"
        )
    else:
        lines.append(f"- aotriton: {aot or 'not found'}")
    lines.append("")
    for kv in sorted({r["kv_heads"] for r in results}):
        rows = [r for r in results if r["kv_heads"] == kv]
        lines.append(f"## kv_heads={kv}" + (" (GQA, Qwen3-VL text encoder)" if kv != Q_HEADS
                                           else " (full MHA, DiT)"))
        lines.append("")
        lines.append("| seq | mask | causal | " + " | ".join(BACKENDS) + " |")
        lines.append("|---|---|---|" + "---|" * len(BACKENDS))
        by_key: dict[tuple, dict] = {}
        for r in rows:
            by_key.setdefault((r["seq"], r["mask_kind"], r["is_causal"]), {})[r["backend"]] = r
        for (seq, mask, causal), cells in sorted(by_key.items()):
            texts = [_cell_text(cells.get(b, {})) for b in BACKENDS]
            lines.append(f"| {seq} | {mask} | {causal} | " + " | ".join(texts) + " |")
        lines.append("")
    counts: dict[str, dict[str, int]] = {b: {"PASS": 0, "FAIL": 0, "OOM": 0} for b in BACKENDS}
    for r in results:
        counts[r["backend"]][r["status"]] = counts[r["backend"]].get(r["status"], 0) + 1
    lines.append("## per-backend totals")
    lines.append("")
    lines.append("| backend | PASS | FAIL | OOM |")
    lines.append("|---|---|---|---|")
    for b in BACKENDS:
        c = counts[b]
        lines.append(f"| {b} | {c.get('PASS', 0)} | {c.get('FAIL', 0)} | {c.get('OOM', 0)} |")
    lines.append("")
    return "\n".join(lines)


# --- entry point ------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="write full results JSON here")
    parser.add_argument("--md", type=Path, help="write the markdown matrix here")
    parser.add_argument("--seq", help="comma-separated sequence lengths (default: plan set)")
    parser.add_argument("--reps", type=int, default=3, help="timed reps per PASS cell")
    parser.add_argument(
        "--launch-blocking", action="store_true",
        help="set HIP_LAUNCH_BLOCKING=1 + AMD_SERIALIZE_KERNEL=3 before torch import")
    args = parser.parse_args()

    # Windows consoles default to legacy code pages (GBK etc.) that cannot
    # encode ✅/❌ — force UTF-8 so printing the matrix can never crash the
    # run after the GPU sweep already paid for it.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.launch_blocking:
        os.environ.setdefault("HIP_LAUNCH_BLOCKING", "1")
        os.environ.setdefault("AMD_SERIALIZE_KERNEL", "3")

    import torch  # after env flags on purpose

    if not torch.cuda.is_available():
        print("ERROR: no CUDA/HIP device visible to torch", file=sys.stderr)
        return 2

    seq_lens = tuple(int(s) for s in args.seq.split(",")) if args.seq else SEQUENCE_LENS
    prop = torch.cuda.get_device_properties(0)
    meta = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "torch_version": torch.__version__,
        "torch_git_version": getattr(torch.version, "git_version", None),
        "hip_version": str(torch.version.hip),
        "gfx_arch": getattr(prop, "gcnArchName", "?").split(":")[0],
        "device_name": torch.cuda.get_device_name(0),
        "aotriton": inspect_aotriton(Path(torch.__file__).parent),
        "launch_blocking": bool(args.launch_blocking),
    }

    cells = build_sweep(seq_lens=seq_lens)
    results = []
    for i, cell in enumerate(cells, 1):
        r = run_cell(cell, reps=args.reps)
        results.append(r)
        print(f"[{i:>3}/{len(cells)}] S={r['seq']:<6} kv={r['kv_heads']} "
              f"{r['mask_kind']:<10} causal={str(r['is_causal']):<5} {r['backend']:<13}"
              f" -> {r['status']}" + (f" ({r['ms']}ms)" if r["ms"] else ""), flush=True)

    print()
    md = render_markdown(results, meta)
    # persist BEFORE printing: a console-encoding failure must never lose data
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"meta": meta, "results": results}, indent=2),
                             encoding="utf-8")
        print(f"wrote {args.json}")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(md, encoding="utf-8")
        print(f"wrote {args.md}")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
