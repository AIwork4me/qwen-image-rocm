"""E5 probe: torch.compile(transformer) on the diffusers stack (2-step smoke).

Expected on this stack (no Triton wheels on Windows ROCm): Inductor fails or
degrades. The exact failure signature IS the Phase-3 data point for
docs/issues/2026-10-30-no-triton-windows-rocm.md (which so far only documents
the FlexAttention fallback).

Run: phase1-diffusers/.venv/Scripts/python.exe -I tools/compile_probe.py
"""

import os
import time
import traceback

os.environ.setdefault("QIR_SDP", "math")  # finding-1 workaround (attempt C)

import torch  # noqa: E402

# finding-1 workaround (attempt C) — must be APPLIED, not just env-set: the
# first probe run only set QIR_SDP without these flags and died in the TEXT
# ENCODER (async hipErrorInvalidValue surfaced at a residual add), which was
# finding #1 again, not a compile result.
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(False)
print("note: math-only SDP applied (finding-1 workaround)")

from diffusers import QwenImage21Pipeline  # noqa: E402

WEIGHTS = os.path.join(os.path.dirname(__file__), "..", "weights", "diffusers-format")

print("loading pipeline (bf16, cpu_offload)...", flush=True)
t0 = time.time()
pipe = QwenImage21Pipeline.from_pretrained(WEIGHTS, torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()
print(f"pipeline loaded in {time.time() - t0:.0f}s", flush=True)

print("applying torch.compile(transformer)...", flush=True)
t0 = time.time()
pipe.transformer = torch.compile(pipe.transformer)

try:
    img = pipe(
        prompt="a cat",
        width=1024,
        height=1024,
        num_inference_steps=2,
        generator=torch.Generator(device="cuda").manual_seed(1),
    ).images[0]
    print(f"COMPILE-SMOKE OK in {time.time() - t0:.0f}s (2 steps incl. compile)")
    out = os.path.join(os.path.dirname(__file__), "..", "results", "raw",
                       "compile_smoke.png")
    img.save(out)
    print(f"saved {out}")
except Exception as exc:  # noqa: BLE001 - the signature is the payload
    print(f"COMPILE FAILURE after {time.time() - t0:.0f}s: "
          f"{type(exc).__name__}: {exc}", flush=True)
    traceback.print_exc()
    print("PROBE-DONE-FAILED")
else:
    print("PROBE-DONE-OK")
