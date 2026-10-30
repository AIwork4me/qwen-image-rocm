# Issue: hipErrorInvalidValue during Qwen3-VL text-encoder forward on Windows ROCm (gfx1100)

- Date found: 2026-10-30
- Status: LOGGED (Phase 1 hard blocker; minimal workaround attempted)
- Suspected layer: PyTorch ROCm Windows kernel / SDPA backend (TBD — async error)
- Phase 4 RCA required

## Environment

See `bench/results/env/snapshot-20261030-212234.json`:
Windows 11 build 26300, AMD Radeon RX 7900 XTX (gfx1100), driver 32.0.21030.2001,
torch 2.12.0+rocm7.14.1 (AMD wheel index, amd-torch-device-gfx1100), HIP 7.14.60850,
Python 3.12.16, diffusers 0.42.1, transformers 5.22.1, accelerate 1.15.0.

## Reproducer

```
phase1-diffusers\.venv\Scripts\python.exe -I phase1-diffusers\generate.py ^
  --prompt-id p1-zh-scene --width 1024 --height 1024 --steps 4 --seed 42 ^
  --out results\raw\smoke
```

All 5 pipeline components load (weights: text_encoder 16.3GB, transformer 13.3GB,
vae 1.3GB) with `enable_model_cpu_offload()`. Failure occurs in the FIRST
text-encoder forward, before any denoising step.

## Full failure (tail)

```
File "...transformers\models\qwen3_vl\modeling_qwen3_vl.py", line 587, in forward
    hidden_states = residual + hidden_states
torch.AcceleratorError: CUDA error: invalid argument
Search for `hipErrorInvalidValue' in https://rocm.docs.amd.com/projects/HIP/en/latest/...
CUDA kernel errors might be asynchronously reported at some other API call...
For debugging consider passing AMD_SERIALIZE_KERNEL=3
Device-side assertion tracking was not enabled by user.
```

Call path: `QwenImage21Pipeline.encode_prompt -> _get_qwen_prompt_embeds ->
text_encoder(**forward_kwargs) -> Qwen3VLModel.forward -> language_model ->
decoder_layer -> residual + hidden_states`.

## Notes

- The reported op (elementwise add) is unlikely to be the real failure —
  async reporting means the kernel that actually failed launched earlier
  (attention? rotary? layernorm kernel?).
- Plain GPU compute works on this stack: `smoke_hip.py` (bf16 matmul 512x512)
  passes, so this is op-shape/backend specific, not a global runtime failure.
- Hypotheses to test in Phase 4 RCA:
  1. SDPA flash-attention backend on ROCm-Windows failing for Qwen3-VL
     attention shapes (head dim / mask dtype) -> try disabling flash SDPA.
  2. Kernel launch config invalid for specific shape (long prompt, 750+
     weight-load iterations observed before forward).
  3. bf16 + specific fused kernel unimplemented on gfx1100 Windows wheels.

## Workaround attempts (2026-10-30, same session)

- [x] A: `AMD_SERIALIZE_KERNEL=3` rerun — same failure, same location, no
  additional kernel info surfaced by serialization.
- [x] B: `torch.backends.cuda.enable_flash_sdp(False)` — **text encoder now
  passes**; failure moved into the DiT forward
  (`transformer_qwenimage21.py:546 torch.cat`, again a benign op = async
  misattribution). So flash SDP is broken on ≥1 path, and the DiT hits
  another failing kernel.
- [x] C: flash + mem-efficient both disabled (math-only SDP) — **END-TO-END
  SUCCESS**: 4-step 1024² generation, exit 0, valid PNG + schema-valid JSON,
  VRAM peak 18.8 GB. First Qwen-Image-2.1 image on this stack.

## Isolated conclusion (for Phase 4 RCA)

Both accelerated SDPA backends (flash, mem-efficient) launch kernels that
fail with hipErrorInvalidValue under torch 2.12.0+rocm7.14.1 Windows
gfx1100 wheels, on the attention shapes used by Qwen3-VL (text encoder)
and the Qwen-Image-2.1 DiT.

Memory side: math SDPA — and flex's no-Triton fallback, which routes
through `flex_attention.py: sdpa_dense -> math_attention` — materialize
the dense L×L scores. At 2048² (L≈16k tokens) that is a single 32.1 GB
allocation: impossible on 24 GB regardless of allocator settings.
At 1024² every prompt fits (zh/en/poster all completed).

CORRECTION (2026-10-31): the first OOM was initially attributed to the
"long English prompt"; it was actually the 2048² resolution of the FIRST
prompt (plan_runs loops prompts outer, resolutions inner). English at
1024² passes on every working backend. Evidence in both tracebacks shows
the identical 32.1 GiB request, consistent with L(2048²).

Backend matrix measured on this stack:

| backend          | text encoder            | DiT @1024²                   | DiT @2048²      |
|------------------|-------------------------|------------------------------|-----------------|
| flash            | ❌ hipErrorInvalidValue  | ❌ hipErrorInvalidValue      | ❌              |
| mem-efficient    | ❌ (fails in DiT path)  | ❌ hipErrorInvalidValue      | ❌              |
| math             | ✅                      | ✅ 3.66 s/step               | ❌ OOM 32.1GB   |
| flex (no triton) | —                       | ✅ ~20–24 s/step             | ❌ OOM 32.1GB (dense fallback) |
| cudnn            | ❌ no kernel            | ❌ no kernel                 | ❌ no kernel    |

Net effect: **2048² generation (Qwen-Image-2.1's native resolution) is
impossible on any backend of the stock Windows ROCm stack on a 24 GB
RDNA3 card today** — the only memory-efficient backends (flash,
mem-efficient, real flex) are exactly the broken/unavailable ones.

Phase 4 should: bisect backend selection, capture the exact failing kernel
(per-backend microbench on the specific head-dims/masks), and check
upstream (PyTorch ROCm SDPA dispatch on Windows / TheRock builds) for
existing reports.

## Additional attempts (same session, after first protocol run died)

- [x] D: DiT backend `flex` via `pipe.transformer.set_attention_backend("flex")`
  + math for text encoder — works at 1024² (en prompt, exit 0, VRAM peak
  20.9 GB) but ~6× slower per step without Triton. At 2048² its dense
  fallback OOMs identically to math.
- [x] E: `_native_cudnn` backend — `RuntimeError: No available kernel`.

Workaround adopted for the Phase 1 baseline: **protocol executed at
1024² only**; 2048² blocked by this issue (evidence: two full OOM
tracebacks in bench runs of 2026-10-31 / 2026-10-31-flex). Both math and
flex variants run at 1024² for backend comparison.
