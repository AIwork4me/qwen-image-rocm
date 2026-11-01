# Issue: first-warmup pagefile thrash (6x step time) with cpu_offload on 32GB-RAM Windows

- Date found: 2026-10-30
- Status: **REPORTED UPSTREAM (2026-11-01, user-approved):**
  [accelerate#4488](https://github.com/huggingface/accelerate/issues/4488)
  (Phase 4 added: thrash cost is backend-dependent — flash immune, dense
  math allocations hit hardest; see W2 evidence)
- Layer: Windows memory management x accelerate cpu_offload interaction

## Context

During the Phase 1 benchmark (run_bench.py, QIR_SDP=math), with weights
totaling ~31 GB and system RAM 31.8 GB:

- cold run (first load): steady 3.6–3.7 s/step at 1024²  (OS file cache hot)
- **warmup run (immediately after): steady 24–26 s/step** — 6x slower,
  total 1076 s; pagefile grew to ~20 GB during this run
- measure run right after: steady 3.66 s/step — fully recovered

## Interpretation (Phase 4 to verify)

`enable_model_cpu_offload()` holds all weights in host memory; Windows
commits/grows the pagefile during the first post-cold generation, and the
growth cost lands on that run's steps. Steady state has no per-step paging
(DiT stays resident in VRAM; only per-prompt text-encoder transfers).

Not a correctness bug; benchmark protocol already excludes warmup runs
from medians. Worth documenting for other 32GB-RAM Windows users: expect
one sacrificial slow run after the first image.

## Environment

snapshot-20261030-212234.json; torch 2.12.0+rocm7.14.1; accelerate 1.15.0;
weights 30.86 GB; RAM 31.8 GB, pagefile 55 GB (20 GB used at observation).
