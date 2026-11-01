# DRAFT comment — ROCm/TheRock#7315 (do NOT post without user approval)

Target: https://github.com/ROCm/TheRock/issues/7315 (OPEN)
Channel: comment — user posts personally (AMD employee) or authorizes gh.
Optional one-line cross-post: ROCm/aotriton#210.

---

Confirmed on **gfx1100 (Radeon RX 7900 XTX)**, Windows 11 26300, with the
**stable** wheel index (`https://repo.amd.com/rocm/whl-multi-arch/`),
`torch[device-gfx1100]==2.12.0+rocm7.14.1` (win_amd64, git
`098172edc887399a593f0c74ae5c40b1fe043801`), Python 3.12.

## Weights-free minimal repro (192 cells)

No model needed — plain `F.scaled_dot_product_attention` sweeps
S ∈ {64,120,256,1024,4096,16384} × {GQA 32Q/8KV, full 32/32} ×
{no-mask, bool-4D, float-additive} × {flash, mem-efficient, math, cudnn},
bf16, head_dim 128, with a ComfyUI-style post-launch flush
(`synchronize()` + dummy `add_().item()`), so launch failures surface as
catchable exceptions per cell.

Results (full matrix in [our repo](
https://github.com/AIwork4me/qwen-image-rocm/blob/main/docs/issues/evidence/sdpa-repro-matrix.md),
raw JSON alongside):

| cells | result |
|---|---|
| flash + no attn_mask (any S ≥ 64, GQA or MHA, causal or not) | `hipErrorInvalidValue` at launch — **fails at the smallest possible shape** |
| mem-efficient, MHA shapes (any mask, any S ≥ 64) | `hipErrorInvalidValue` at launch |
| mem-efficient + GQA (8 KV heads) | `No available kernel` (CPU-side shape rejection — expected, not the bug) |
| flash + explicit mask | `No available kernel` (CPU-side mask rejection — expected) |
| cudnn | `No available kernel` (not built) |
| math | PASS ≤ S=4096 (0.26→90 ms, quadratic); OOM at S=16384 (32 GB dense scores) |

Real-world impact (why we chased this): Qwen-Image-2.1 on diffusers fails
end-to-end because the text encoder (GQA, unmasked/causal) and DiT (dense)
both land on the broken launches; 2048² generation is impossible on any
backend because the only memory-efficient ones are exactly the broken ones.
ComfyUI survives only because its startup probe
(`comfy/model_management.py`, `aotriton_supported()`) hits the same
failure and auto-disables flash.

`HIP_LAUNCH_BLOCKING=1` + `AMD_SERIALIZE_KERNEL=3` surface the same
message with no additional kernel attribution.

## Wheel AOTriton evidence (2.12.0+rocm7.14.1 win_amd64)

- `torch/lib/aotriton.images/amd-gfx110x/__signature__`:
  `AOTRITON_GIT_SHA1=6e00ef3e335b45dfb49065259533b59c68995bfe`
  (14 arches incl. gfx1100; flash kernels `attn_fwd.zip` + 4 bwd zips)
- `torch/lib/aotriton_v2.dll`: exports `flash@v3@aotriton` (v3 API)
  symbols; no embedded version/git string; the pytorch-side
  `__AOTRITON_CI_COMMIT` pin is not exposed anywhere in the installed
  wheel (`torch.__config__.show()` has no aotriton field) — if useful to
  the maintainers, the images SHA above is the concrete local artifact to
  diff against the 2.12 build's pin (the release/2.12 fix d1abf10 lineage).

## Same-index good build check

Per #7992 we also verified `torch[device-gfx1100]==2.12.0+rocm7.14.0`
from the **same** `whl-multi-arch` index on the same machine (fresh venv,
torch git `13eab2b3ef4e03999247f063bc2dde01c94e9eaa`): the identical
192-cell sweep shows **zero launch failures** — every cell that 7.14.1
fails with `hipErrorInvalidValue` PASSES on 7.14.0 (flash, unmasked,
all S up to 16384: 0.09 ms @64 → 116-163 ms @16384; mem-efficient on all
MHA shapes incl. explicit masks; S=16384 completes in ~120-200 ms where
math OOMs on the 32 GB dense allocation). The only remaining reds are the
same CPU-side `No available kernel` rejections on both builds (flash +
explicit mask, mem-efficient + GQA, cudnn).

Notably the two builds ship **different AOTriton artifacts**:

| | 2.12.0+rocm7.14.1 (broken) | 2.12.0+rocm7.14.0 (good) |
|---|---|---|
| images dir | `amd-gfx110x` | `amd-gfx11xx` |
| `__signature__` SHA1 | `6e00ef3e335b45dfb49065259533b59c68995bfe` | `dd1b68b604b5258ee7a9f7b66ad95e7a82c18065` |
| torch git | `098172ed…` | `13eab2b3…` |
| `aotriton_v2.dll` v3 symbols | yes | yes |

i.e. the stable channel currently serves two adjacent builds whose
runtime/images pairings differ, and only the newer one is broken on
Windows gfx1100 — consistent with the runtime/images mismatch lineage
described in this issue and #7992.

## Channel hygiene note

As of 2026-11-01 the stable `repo.amd.com/rocm/whl-multi-arch/` index
still resolves `torch[device-gfx1100]` (latest 2.12.0) to the known-broken
`+rocm7.14.1` build for Windows users. If a rebuild/re-spin of the stable
pin is planned, this data point (repro + images SHA) may help confirm the
fixed lineage. Related: #7992 (closed), ROCm/pytorch#3569 (merged).
