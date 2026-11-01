# DRAFT — transformers/diffusers SDPA failure resilience (finding #5)

**POSTED 2026-11-01 (user-approved) as transformers issue:** https://github.com/huggingface/transformers/issues/50211

Target: huggingface/transformers (+ diffusers follow-up)
Channel: issue first (design discussion), then PR. Root cause is upstream
in the torch wheel (TheRock#7315) — this is NOT a dup of it; it asks how
HF libraries should behave when the selected SDPA backend fails at launch.

---

## Summary

On torch builds where a fused SDPA backend launches kernels that fail with
`hipErrorInvalidValue` (Windows ROCm gfx1100, torch 2.12.0+rocm7.14.1 —
root-caused upstream in ROCm/TheRock#7315, AOTriton runtime/images
mismatch), a plain `F.scaled_dot_product_attention` call raises:

```
torch.AcceleratorError: CUDA error: invalid argument
Search for `hipErrorInvalidValue' in ...rocm docs...
CUDA kernel errors might be asynchronously reported at some other API call
```

Two user-facing problems:

1. **Misleading attribution**: the error surfaces at a *later, benign* op
   (an elementwise add) because it is asynchronous. Users bisect the wrong
   layer. (Our first report blamed the residual add;
   `transformers/models/qwen3_vl/modeling_qwen3_vl.py:587` was innocent.)
2. **No recovery path**: auto-selection commits to flash/mem-efficient and
   the whole forward dies, even though the math backend works.

## The ComfyUI contrast (probe-and-fallback works)

ComfyUI on the same broken stack probes at startup — construct
`SDPAParams`, launch one tiny flash SDPA, `synchronize()`, then a dummy
`tensor.add_(1).item()` to flush the async error — catches it, logs
`Could not run flash attention, disabling it`, disables the backend, and
everything downstream works (sub-quadratic kernel).
Pattern: `comfy/model_management.py` `aotriton_supported()`
(ComfyUI 0.43.0 b5a4321, lines ~497-527). End users see a working product
on a stack where diffusers/transformers pipelines hard-fail.

## Proposal (two options, prefer the smaller one first)

**Option A — actionable error translation (small, no behavior change):**
when an SDPA call inside a text-encoder/DiT forward raises an accelerator
error mentioning `invalid argument`/`hipErrorInvalidValue`, re-raise with
a hint: "a fused SDPA backend (flash/mem-efficient) may be failing on
this build; try `torch.nn.attention.sdpa_kernel(SDPBackend.MATH)` or
disable the failing backend". One helper + one catch-site per integration
(`transformers/integrations/sdpa_attention.py`,
`diffusers/models/attention_dispatch.py`).

**Option B — probe-and-fallback (bigger):** one cheap startup probe per
process (the ComfyUI pattern, ~10 lines) that downgrades backend priority
when a fused backend fails at launch; opt-out via env var. This is what
saves ComfyUI users today; doing it in the libraries would fix every HF
pipeline on this class of broken builds.

Happy to PR either (A first) — the probe pattern is already field-tested
in ComfyUI and we have a 192-cell weights-free repro matrix
([evidence](https://github.com/AIwork4me/qwen-image-rocm/blob/main/docs/issues/evidence/sdpa-repro-matrix.md))
showing exactly which backends fail on which shapes.

Environment: Windows 11 26300, RX 7900 XTX (gfx1100), torch
2.12.0+rocm7.14.1 (repo.amd.com whl-multi-arch), transformers 5.22.1,
diffusers 0.42.1; failing models: Qwen3-VL text encoder (GQA) and
Qwen-Image-2.1 DiT (dense, bool-4D segment masks).
