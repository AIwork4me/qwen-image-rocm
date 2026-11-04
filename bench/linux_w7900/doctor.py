"""Doctor: Linux lab preflight checks (CLI-accessible P0 evidence refresh)."""

from __future__ import annotations

import json
from pathlib import Path

from . import lab_env, manifests


def run(quick: bool = False) -> int:
    checks: list[dict] = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL",
                       "detail": str(detail)[:400]})

    snap = lab_env.build_snapshot()
    problems = lab_env.check_gpu_expectations(snap)
    add("gpu_gfx1100_single", not problems, problems or
        f"{snap.get('gpu_name')} / {snap.get('gfx_arch')} / {snap.get('total_vram_mb')}MB")
    add("torch_rocm", bool(snap.get("cuda_available")),
        f"torch {snap.get('torch')} hip {snap.get('hip')}")
    add("comfyui_pinned", snap.get("comfyui", {}).get("tree_marker_ok"),
        f"v{snap.get('comfyui', {}).get('version')} @ {snap.get('comfyui', {}).get('pinned_commit', '')[:12]}")
    add("weights_integrity", _weights_ok(),
        "sha256 vs pinned digests (bench/quickstart_config.py)")

    try:
        from . import server as server_mod

        add("server_module", True, "importable")
    except Exception as exc:  # noqa: BLE001
        add("server_module", False, exc)

    if not quick:
        try:
            import torch

            q = torch.randn((1, 8, 128, 64), dtype=torch.bfloat16, device="cuda")
            with torch.nn.attention.sdpa_kernel(
                    torch.nn.attention.SDPBackend.FLASH_ATTENTION):
                o = torch.nn.functional.scaled_dot_product_attention(q, q, q)
            torch.cuda.synchronize()
            add("flash_sdpa_probe", True, "flash attention launches + syncs on gfx1100")
        except Exception as exc:  # noqa: BLE001
            add("flash_sdpa_probe", False, exc)
        try:
            import subprocess

            r = subprocess.run(["rocprofv3", "--version"], capture_output=True,
                               text=True, timeout=20)
            add("rocprofv3", r.returncode == 0, (r.stdout + r.stderr).strip()[:200])
        except Exception as exc:  # noqa: BLE001
            add("rocprofv3", False, exc)

    env_ref = lab_env.write_snapshot()
    out = {"verdict": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
           "checks": checks, "snapshot": env_ref}
    p = lab_env.RESULTS_ROOT / "doctor.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    for c in checks:
        print(f"{c['status']:4s} {c['check']}: {c['detail']}")
    print(f"\nverdict: {out['verdict']}  evidence: {p}")
    return 0 if out["verdict"] == "PASS" else 1


def _weights_ok() -> bool:
    import subprocess
    import sys

    rels = [
        "diffusion_models/qwen_image_2.1_bf16.safetensors",
        "diffusion_models/qwen_image_2.1_turbo_bf16.safetensors",
        "diffusion_models/qwen_image_2.1_int8_convrot.safetensors",
        "diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors",
        "text_encoders/qwen3vl_8b_bf16.safetensors",
        "vae/qwen_image_2.1_vae_bf16.safetensors",
    ]
    ok = True
    for rel in rels:
        r = subprocess.run(
            [sys.executable, "-I", str(lab_env.REPO / "bench" / "quickstart_config.py"),
             "verify-weight", "--rel", rel], capture_output=True, text=True)
        try:
            ok = ok and json.loads(r.stdout)["ok"]
        except Exception:  # noqa: BLE001
            ok = False
    return ok
