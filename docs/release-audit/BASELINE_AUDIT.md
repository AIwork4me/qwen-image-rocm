# Baseline release audit — 2026-11-01

Independent audit performed before release-readiness work, per the
release-ready-v0.1.0 mandate. Historical benchmark data was treated as
read-only; nothing in `bench/results/` was modified.

## Base commit

- **Base commit:** `e858d89` (`docs(phase4/W3-posted): all 6 approved upstream
  contributions published …`) — pushed to `origin/main` by the prior session.
- **Work branch:** `release/trending-ready-v0.1.0` (this audit and all
  release work lands here; `main` is not auto-merged).
- **Remote:** https://github.com/AIwork4me/qwen-image-rocm (default branch
  `main`, issues enabled).
- **Working tree at audit start:** clean (one doc edit left over from the
  prior session was committed by that session as `e858d89` while this audit
  was starting; verified no concurrent writer remained).

## Current real technical state

| Area | State at base commit |
|---|---|
| Phases 0–4 | Complete: repo + diffusers baseline (P1), ComfyUI baseline (P2), optimization loop with quality gates (P3), RCA + upstream contributions (P4) |
| ROCm stack (verified baseline) | torch `2.12.0+rocm7.14.1` (AMD wheel index), ComfyUI pinned commit `b5a43215`, CPython 3.12.16, Windows 11 native, RX 7900 XTX (gfx1100) |
| Alternate stack (measured, not default) | `2.12.0+rocm7.14.0` all-green SDPA (flash 3.4× vs math); nightly `2.15.0+rocm10.3.0a` all-green — decision sheet in `docs/phase4-stack-switch-decision.md`, baselines unchanged |
| Test suite | 55 tests, all pass locally (dir `image`); CPU-only, no GPU required |
| CI (GitHub) | **RED on every main push** — see below |
| Upstream contributions | 6/6 posted & linked (`docs/upstream/INDEX.md`): TheRock#7315 comment, transformers#50211, accelerate#4488, hf#4196 comment, comfy-kitchen#292, ComfyUI#17469/#17470 |
| Repo metadata | **No description, no topics, no homepage** (gh-verified) |

## Verified capabilities (with evidence)

1. **1K generation, 5.2–5.5× warm speedup** — Turbo-8-step int8 DiT + ck
   attention: 9.1 s/image @1024² vs same-session bf16-40 shadow control
   (48.2–50.2 s), n=9 across 3 prompts, protocol v1.3
   (`bench/results/2026-11-01-phase3-summary/report.md`).
2. **2048² generation unlocked** — int8 route: 328 s @40 steps;
   42.2 s Turbo-int8 @8 steps (single probe each:
   `…-e2-int8-dit-te-2048-probe/`, `…-e2-turbo-int8-2048-probe/`).
3. **Quality gates** — human verdicts (A1–A4 无感 / A5 略降 rejected) +
   independent AI second opinion, 0 divergence ≥1 grade; LPIPS noise floor
   0.0000 (`bench/results/AI_JUDGE_RESULTS.json`, REVIEW_PACK.md).
4. **ROCm findings 1–5 root-caused with evidence** — flash/mem-eff SDPA
   launch failures upstream-root-caused (TheRock#7315 AOTriton mismatch),
   weights-free 192-cell repro, remediation measured (7.14.0 flash
   1.07 s/step @1024², 3.4× vs math, −1.9 GB VRAM).
5. **Repro protocol** — `reproduce.ps1` (Phase 1 diffusers) with mandated
   AMD wheel install, HIP smoke, ModelScope weights, PyPI-swap guard.

## Unverified / over-broad claims found (must be fixed before release)

| # | Claim as currently worded | Reality per raw evidence | Disposition |
|---|---|---|---|
| U1 | "Recommended production config: Turbo int8 DiT **+ int8 TE + ck + `--disable-smart-memory`**" (phase3-summary; CHANGELOG repeats) | The triple was **never measured together** — `p3-turbo-int8-ck` manifest uses **bf16 TE, no nosmart flag**; summary itself notes "not yet measured as a triple" | Measure on GPU this session (manifest `p3-turbo-int8-ck-te-nosmart-1024x1024`); until then README/matrix mark the combo PROJECTED, measured-pairs only |
| U2 | 9.1 s presented as headline speed | Warm, same-prompt, cached-TE steady state (records show `CLIPTextEncode` in `cached_nodes`, `text_encode_s: 0`). Cold/fresh/warm never reported as separate user-facing numbers | Add `REAL_WORLD_LATENCY.md`; README headline must carry warm qualifier + cold/fresh numbers |
| U3 | "2048² unlocked" | Single probe per config; no multi-seed/multi-prompt repeats, no OOM-recovery or long-run stability data | Re-probe this session + `2048_VALIDATION.md` with explicit evidence tiers |
| U4 | "5.2–5.5×" speedup framing | Paired vs same-session bf16-40 control, warm-only, quality = user verdict "distance" (images necessarily differ), not lossless | Keep number, bind qualifiers in matrix; forbid "lossless" wording for turbo/ck |
| U5 | `reproduce.ps1 -Full` header says "2048 blocked on every working backend" | True for bf16/stock 7.14.1 at time of writing; Phase 3 unlocked 2048 via int8 route — script comment + README stale | Fix comment; quickstart becomes the user path |

## Known issues (carried, not release blockers)

- Finding 1 (SDPA launch failures on 7.14.1) — workaround `QIR_SDP=math`
  baked into launchers; upstream tracked.
- Finding 3 (no Triton on Windows ROCm) — torch.compile blocked; closed as
  verified distribution gap.
- Finding 4 (pagefile thrash on first warmup, 32 GB RAM hosts) — documented.
- `bench/run_variant.ps1` killed ANY process listening on its port before
  starting a server — user-hostile hazard (fixed in this branch:
  own-orphans-only + spare-port fallback).
- Local absolute paths (`C:\Users\Rocm\…`) appear inside committed historical
  server logs — retained deliberately as evidence (history is read-only);
  new logs get a scrub pass before commit (see LEGAL_AND_ATTRIBUTION.md).

## Historical evidence sources (read-only)

- `bench/results/2026-11-01-phase3-summary/report.md` + per-experiment dirs
  (JSON records schema-validated, `quality.md`, grids, server logs,
  attention evidence).
- `bench/results/2026-10-31-*` (Phase 1/2 baselines), `bench/results/env/`
  snapshots, `docs/issues/evidence/` (Phase 4 repro matrices + logs).
- User + AI quality verdicts: `bench/results/REVIEW_PACK.md`,
  `AI_JUDGE_RESULTS.json`.

## CI status at audit time

- Every recent `main` push: **failure** (runs 41263125835…41279001968).
- Root cause (verified from run 41279001968 log):
  `tests/test_core.py::test_core_exports` asserted
  `core.REPO.name == "image"` — the local checkout directory name. GitHub
  checks out as `qwen-image-rocm` → assertion fails on any clean CI clone.
  54/55 tests passed; the failure is a local-dir-name coupling, not a code
  defect.
- Fix on this branch: `e6a6f11` — checkout-dir-independent assertions
  (`REPO` must be the root containing `bench/core.py`), CI renamed to an
  explicit **CPU test gate** + new manual **GPU hardware validation**
  workflow (self-hosted Radeon; hosted runners make no GPU claims).
  Local: 55/55 pass, ruff clean.

## Fix priorities for this branch

1. **P0** close U1 (measure the triple), then align every public claim to
   evidence via `docs/benchmarks/CLAIM_EVIDENCE_MATRIX.md`.
2. **P0** real-user latency doc (cold / fresh / warm) + 2048 validation doc.
3. **P0** `quickstart.ps1` Fast/Quality user path (reusing the verified
   ComfyUI driver), port-safe process handling, no silent CPU fallback.
4. **P1** README product page (en + zh mirror) with real gallery; GitHub
   metadata (description/topics), issue/PR templates, public tracking
   issues, roadmap; legal/attribution doc; v0.1.0-rc1 (owner-gated).
5. **P2** launch kit.
