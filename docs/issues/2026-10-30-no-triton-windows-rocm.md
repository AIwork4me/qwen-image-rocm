# Issue: no Triton wheels for Windows ROCm in AMD's wheel index; FlexAttention degraded to slow fallback

- Date found: 2026-10-30
- Status: LOGGED
- Layer: AMD wheel distribution (repo.amd.com/rocm/whl-multi-arch) / PyTorch
  Windows-ROCm stack

## Evidence

```
> python -m pip install triton --index-url https://repo.amd.com/rocm/whl-multi-arch/ --dry-run
ERROR: Could not find a version that satisfies the requirement triton (from versions: none)
```

(torch 2.12.0+rocm7.14.1 gfx1100 stack installed from the same index works,
so the index itself is reachable and functional.)

Consequence: `torch.compile` and FlexAttention have no Triton codegen on
Windows ROCm. Measured effect (diffusers `flex` attention backend on the
Qwen-Image-2.1 DiT, 1024², 40-step equivalent):

- math SDPA: ~3.66 s/step (but OOMs at longer prompts / 2048² — see the
  SDPA issue doc)
- flex (no Triton, fallback path): ~20–24 s/step — roughly 6× slower

torch's flop_counter separately warns "triton not found", confirming the
stack-wide absence.

## Impact on this project

Phase 1 baseline must run with the flex backend (only backend that
completes the full protocol), so baseline per-step numbers carry this
slowdown. Phase 3 should revisit once a Windows Triton exists; Phase 4
should check TheRock's Windows builds for triton availability and, if
absent upstream, this is a distribution gap worth raising.

## Environment

snapshot-20261030-212234.json; Python 3.12.16; torch 2.12.0+rocm7.14.1.
