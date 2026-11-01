# Phase 4 decision sheet: should the mandated stack move to 2.12.0+rocm7.14.0?

Status: **USER DECIDES** — the mandated baseline (torch
2.12.0+rocm7.14.1 via `repo.amd.com/rocm/whl-multi-arch/`) is NOT changed
by Phase 4. This sheet lays out the measured trade-off (2026-11-01).

## What changed

The 7.14.1 wheel's flash/mem-efficient SDPA launch failures (finding 1,
upstream-root-caused as TheRock#7315/#7992 AOTriton runtime/images
mismatch) are **absent from 2.12.0+rocm7.14.0 on the same index** —
verified with the 192-cell repro (0 launch failures vs 48) and
end-to-end: first no-workaround diffusers generation on this machine.

## Measured cost/benefit (diffusers, 1024² bf16, p1, cpu_offload)

| | 7.14.1 + math (baseline) | 7.14.0 + flash |
|---|---|---|
| steady s/step | 3.66 | **1.07 (3.4x)** |
| VRAM peak | 18.8 GB | **16.9 GB (−1.9)** |
| workaround needed | QIR_SDP=math everywhere | none (default works) |
| 2048² bf16 | attention OOM (32.1 GB dense) | attention passes; **VAE decode** OOMs (20.25 GB conv) — still blocked, different reason |
| math fallback | works | works (identical kernel speed) |
| stack age | current stable pin | one build older (same 2.12.0 torch) |

Phase-3 ComfyUI results are NOT affected either way: ComfyUI's default
attention never used the broken kernels (startup probe → sub-quadratic
fallback; ck bypasses torch SDPA entirely).

## Risks of switching

1. **Baseline continuity**: Phase 1-3 numbers were all measured on
   7.14.1+math. A switch re-baselines every future comparison (mitigated:
   both venvs can coexist; snapshots now record the SDPA probe, so any
   run's stack is self-describing).
2. **7.14.0 is a moving target**: the stable index re-pins freely (that
   is how 7.14.1 landed); pinning `==2.12.0+rocm7.14.0` in commands is
   exact, but future deps (torchvision etc.) must match manually.
3. **Older AOTriton images set** (`amd-gfx11xx`, sha dd1b68b6…) — fine
   today, but any future "just reinstall latest" drifts back to whatever
   the index serves (possibly broken again until upstream re-spins).

## Options

- **A. Stay on 7.14.1+math** (zero churn; keeps 3.4× attention on the
  table unused; diffusers route stays on the workaround).
- **B. Switch the mandated stack to `==2.12.0+rocm7.14.0`** (fastest
  diffusers route today; re-baselines future comparisons; depends on a
  build the stable index no longer advertises as latest).
- **C. Keep baselines frozen; make 7.14.0 a documented opt-in profile**
  (`phase4-diag-7140` already exists and is measured; document the
  one-line install for users who want flash now). Recommended as the
  next step regardless of A/B — nothing is lost, evidence stays
  reproducible, and the choice can be revisited when upstream ships a
  fixed newer build (then a switch costs nothing).

Recommendation: **C now, B when a fixed build is re-pinned as latest**
(unblocks flash without freezing the project to an aging build).
