# Issue: no Triton wheels for Windows ROCm in AMD's wheel index; FlexAttention degraded to slow fallback; torch.compile dead at backend creation

- Date found: 2026-10-30
- Status: LOGGED (torch.compile signature added 2026-11-01, Phase 3 E5)
- Layer: AMD wheel distribution (repo.amd.com/rocm/whl-multi-arch/) / PyTorch
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

## torch.compile signature (E5 probe, 2026-11-01, tools/compile_probe.py)

`torch.compile(pipe.transformer)` + a 2-step 1024² generation fails at
Inductor BACKEND CREATION — before any kernel compilation is attempted —
with the exact upstream error:

```
torch._inductor.exc.TritonMissing: Cannot find a working triton
installation. Either the package is not installed or it is too old.
  at torch/_inductor/scheduler.py:6647 create_backend
```

Probing notes:

1. With the math-SDPA workaround applied (finding 1), the Qwen3-VL text
   encoder passes and the failure isolates cleanly to Inductor → no
   fallback-to-eager occurs (dynamo does not catch TritonMissing; the
   pipeline call raises).
2. First probe run WITHOUT applying the workaround (env var set, flags not
   called) died in the text encoder instead — async `hipErrorInvalidValue`
   surfacing at a residual add in `modeling_qwen3_vl.py:587` — i.e. finding
   1 masks compile probing unless handled first. Worth remembering for the
   minimal-repro in Phase 4.

## Impact on this project

Phase 1 baseline must run with the flex backend (only backend that
completes the full protocol), so baseline per-step numbers carry this
slowdown. torch.compile is unavailable to Phase 3 optimization (E5 =
recorded blocked). Phase 4 should check TheRock's Windows builds for triton
availability and, if absent upstream, this is a distribution gap worth
raising; web check 2026-10-31 found no installable production path on the
mandated repo.amd.com stack (triton-land/TheRock upstreaming work is the
thing to watch).

## Environment

snapshot-20261030-212234.json; Python 3.12.16; torch 2.12.0+rocm7.14.1.
