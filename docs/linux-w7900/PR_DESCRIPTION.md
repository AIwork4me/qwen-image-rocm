# DRAFT PR — feat/linux-w7900-optimization-lab

## Title: feat: Linux W7900 optimization lab — baseline → profiling → less/faster/parallel compute → BEST 6.12× (quality verdict pending)

> **Note (from the lab environment):** this branch was built and physically
> validated on the W7900 lab host, whose egress proxy blocks github.com git
> endpoints, so the branch could not be pushed from there. The owner should
> push `feat/linux-w7900-optimization-lab` (HEAD `3c32e607`, 4 commits on top
> of the byte-verified import of main @ `acc318fc`) and open this PR.
> Nothing merges without owner review; no release is created.

## Scope

Adds `bench/linux_w7900/` + `docs/linux-w7900/`: a reproducible Linux ROCm
inference-optimization lab for Qwen-Image-2.1 on a single Radeon PRO W7900
(gfx1100, 48 GB), reusing the existing protocol core, prompts, schema and
quality-gate tooling. Windows files are untouched (verified: empty diff vs
import baseline for all historical results/manifests/docs).

## Experiment progress matrix

| ID | Config | Status | Warm 1024² | vs B0 | VRAM | Quality |
|---|---|---|---|---|---|---|
| B0 | bf16 40-step baseline | PASS (2 sessions) | 55.21 s | 1.00× | 37.7 GB | reference |
| L1 | Turbo 8-step | PASS | 12.13 s | 4.55× | 37.7 GB | distance, review pending |
| L1O | Turbo official σ | PASS | 12.07 s | 4.57× | 37.7 GB | distance, review pending |
| F1 | ck attention | PASS | 45.09 s | 1.22× | 37.7 GB | distance, review pending |
| F2 | INT8 DiT | PASS | 51.09 s | 1.08× | 31.0 GB | **fidelity 0.005–0.031 near-lossless** |
| LF1/2/3 | combos | PASS | 10.03/9.02/9.02 s | ≤6.12× | 31–37.7 GB | distance, review pending |
| H1 | CPU TE | PASS (negative) | TE 137–207 s | — | −16.8 GB | cond parity ✓ |
| H2 | 4-req pipeline | PASS (negative) | 737 vs 51 s | — | — | overlap proven 50.4 s |
| F4 | torch.compile | NOT_RUN (rejected w/ profiling evidence) | — | — | — | — |
| **BEST** | Turbo INT8 + default attn | PASS, rerun ✓ | **9.02 s** | **6.12×** | 31.0 GB | **PENDING_HUMAN_REVIEW** |

## Key results

- Profiling (rocprofv3 on the real server): GEMM 61.3% / attention 32.4% of
  GPU-busy 97.8%; 1 sync, ~0 copies per generation.
- BEST independently re-run in a fresh process: 9.020/9.023/9.020 s.
- 146 schema-valid run records; noise floor LPIPS 0.0000 (9/9).
- Full claim→evidence matrix: `docs/linux-w7900/CLAIM_EVIDENCE_MATRIX.md` (25 claims).

## Evidence references

`bench/results/linux-w7900/` (records, quality grids, native typography crops,
B0+BEST sample images, charts, env snapshots) ·
`docs/linux-w7900/` (P0–P6 reports, reproduction guide, lecture package,
final engineering report, open issues).

## Remaining blockers / owner review requirements

1. **Human three-tier quality verdict** (无感/略降/不可接受) on the committed
   grids — especially Chinese typography at native resolution
   (`quality-BEST/quality_crops_poster.png`). Nothing is quality-approved
   until recorded.
2. Push the branch + open/merge this PR (blocked from the lab network).
3. Optional owner decisions: 2048² exploration (gated on the verdict),
  committing full raw image sets (~150 MB) vs the current curated samples.

## Companion teaching repository

All of this work is additionally packaged as a standalone classroom course:
**qwen-image-inference-tuning-course** (separate repo) — syllabus + 8 teaching
modules + the same runnable lab (`python -m lab …`) + the same evidence set,
licensed MIT (code) / CC-BY-4.0 (texts & data), with attribution to this
project. Ideal for the 2026-11-19 lecture and student challenges.
