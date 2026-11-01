# Changelog

## 2026-11-01 — Final release closure (PR #7, round 3)

Last fidelity-semantics hardcode removed from the quality-gate generator:
the FIDELITY note said "closer to the bf16 reference" regardless of the
actual baseline — wrong for the r1-triple gate whose baseline is E8. Now:
"closer perceptual similarity to the specified baseline image; LPIPS is
not an absolute image-quality score" (docstring, CLI help, and generated
markdown all baseline-agnostic; fidelity/distance distinction preserved).
r1-triple quality.md regenerated with byte-identical numbers (p1
0.0583/0.0748 · p2 0.0115/0.0150 · p3 0.0137/0.0154 — deterministic
rerun). Anti-regression: 6-case semantics suite (true-bf16 / E8 / future
non-bf16 / missing-metadata fail-closed / committed-artifact agreement /
not-a-quality-score) + evidence pinning suite that RECOMPUTES all quoted
r1/r3 medians from the committed JSON records (8.30/9.06/8.09 s @1024²;
40.268/40.324/40.362 s, range 40.236–40.445 @2048²; warm records verified
as cache-hit runs, never fresh-prompt). Audit docs layered: historical
round-1 sections marked "Historical Round-1 Snapshot — Superseded" with a
Current Final Release Assessment on top; no future SHAs committed.
OWNER_QUALITY_REVIEW.md added — the human-decision pack for issue #5
(configs, sample matrix, LPIPS table, direct image links, per-prompt
visual dimensions, verdict scale, non-binding AI observations clearly
labeled). 101/101 tests, ruff clean; no inference-path changes (round-2
GPU evidence stands); no history rewrites; links + zh/en audits pass.

## 2026-11-01 — Independent-review revision (PR #7, round 2)

P0: r1-triple quality.md baseline relabeled from a hardcoded "bf16, 40
steps" to the actual baseline (E8 turbo-int8/bf16-TE/ck, 8 steps), now
derived from run records + machine-readable quality.json; LPIPS per-prompt
mapping corrected in every doc/PR/issue (p1=0.058, p2=0.012, p3=0.014 —
original values unchanged, rerun deterministic). Process ownership rebuilt
PID-first (bench/portops.ps1): existing listeners are never touched
(spare-port fallback), teardown kills only the tree this run started,
command-line string matching removed entirely; live dual-checkout test
passed (decoy server with "phase2-comfyui" in its command line survived a
full run untouched). Found & fixed a real PS 5.1 hazard while testing: the
FIRST CIM/NetTCPIP query in a fresh process can transiently return empty —
the port check now bind-probes instead (same syscall as the server).
Weight integrity hardened: revision aacf31a6 pinned, sha256 table embedded
(cross-verified LFS-pointer vs local hashes 8/8), digests enforced for
pre-existing files (size-only was a bypass), stamp cache keyed size+mtime,
same-size-wrong-content injection tests added. ComfyUI commit drift now
fails closed (-AllowComfyCommitDrift = experimental, recorded
stack_verified=false in provisioning.json); -SkipSetup still verifies
torch/commit/digests. Unified cold-start vocabulary (Server boot /
Ready-to-first-image / Full cold start / Warm mean+median) in script and
docs. Triple grid verdict remains PENDING (#5). P1: gpu-validation.yml
provisions a clean checkout (no venv/weights assumptions); step-times
audit tool (105/337 records carry partial step_times_s — step-1 events
lost; no published number derives from them); quickstart local results
gitignored; run_variant refuses to clobber existing records
(-OverwriteResults to override). 91+ CPU tests, ruff clean.

## 2026-11-01 — Release readiness (v0.1.0-rc1)

**Quickstart**: `.\quickstart.ps1 -Mode Fast|Quality` — one command from
clone to first image (env/GPU/gfx1100 checks, pinned venv + AMD wheels,
pinned ComfyUI commit, sha256-verified resumable weight downloads,
Radeon-required health gate, benchmark-driver smoke with cold/warm report;
no silent CPU fallback; port-safe process handling everywhere). Dogfooded
on the target GPU in both modes (Fast: boot 8.1 s / cold 12.1 s / warm
8.11 s; Quality: cold 59.4 s / warm 46.4 s).
**The production triple finally measured as a whole** (turbo int8 DiT +
int8 TE + ck + `--disable-smart-memory`): warm medians 8.30/9.06/8.09 s
(n=9), fresh-prompt +1.2 s, cold 17.1 s, sampled VRAM peak ≈ 7.7 GB; LPIPS
fidelity vs e8: 0.058/0.012/0.014 (formal grid verdict pending owner).
**2048² re-probed** on the triple config: warm 40.2 s / cold 43.3 s,
sampled peak ≈ 8.3 GB (second session, second prompt — probe tier).
**CI fixed & split**: checkout-dir-independent repo-root test (root cause
of red main), explicit CPU test gate + manual self-hosted GPU validation
workflow. **Evidence docs**: claim→evidence matrix, real-world latency
(cold/fresh/warm split with sampling semantics), 2048 validation ledger,
quality methodology (LPIPS semantics + verdict ledger), baseline audit.
**Product README** (en/zh mirrors) with real gallery + provenance, support
matrix, quickstart, forbidden-framings enforcement; social preview built
from real outputs (CJK-verified). `bench/run_variant.ps1` no longer kills
unrelated processes on its port. Issue/PR templates, troubleshooting,
legal & attribution, v0.1.0-rc1 (owner-gated). 66 CPU tests green, ruff
clean; secret scan clean on all new logs.

## 2026-11-01 — Phase 4: RCA verification + upstream contribution track

Finding 1 (flash/mem-efficient SDPA `hipErrorInvalidValue`) **verified
against upstream root cause** (TheRock#7315/#7992 AOTriton runtime/images
mismatch): weights-free 192-cell repro (`tools/repro/sdpa_repro.py`, no
model needed) shows launch failures from S=64 on 7.14.1 — and **zero**
on `2.12.0+rocm7.14.0` from the same index. Measured fix benefit: flash
**1.07 s/step @1024² (3.4x vs math, −1.9 GB VRAM)**, first
no-workaround generation; 2048² bf16 now VAE-bound (20.25 GB conv OOM),
not attention-bound. Wheel aotriton evidence recorded (7141 `amd-gfx110x`
sha 6e00ef3e vs 7140 `amd-gfx11xx` sha dd1b68b6). Finding 3 closed as
verified distribution gap (TheRock PR#4006 merged, no public wheels).
`tools/snapshot_env.py` extended (transformers/diffusers versions +
per-backend SDPA probe; discriminates broken/good builds in ~15 s).
Six upstream drafts staged in `docs/upstream/` (TheRock#7315 comment,
transformers/diffusers SDPA resilience, accelerate pagefile issue,
hf#4196 comment, comfy-kitchen RDNA3-Windows data, ComfyUI backlog) —
**user-approved and all posted 2026-11-01** (links in
`docs/upstream/INDEX.md`: TheRock#7315 comment, transformers#50211,
accelerate#4488, hf#4196 comment, comfy-kitchen#292, ComfyUI#17469/17470). Stack-switch decision sheet at
`docs/phase4-stack-switch-decision.md` (baselines unchanged). Ruling:
`patches/` intentionally NOT created — the fixes live in upstream
versions/builds (7.14.0, upstream merged patches), not in local patches
we would have to maintain; the repro + drafts are the durable artifacts.

## 2026-11-01 — Phase 3: optimization loop (protocol v1.3)

**1024-square: 5.2-5.5x faster (48s -> 9.1s)** via Turbo-8-step + native
int8 DiT + ck-attention (+ --disable-smart-memory). **2048-square unlocked**
(328s @40 steps; 42s with turbo-int8) — was impossible on bf16. Native int8
is near-lossless (LPIPS 0.004-0.031); w4a8 TE fails quality (0.41 max);
VAEDecodeTiled, --highvram, --fast fp16_accumulation all rejected with data.
torch.compile blocked: `TritonMissing` at inductor backend creation.
Measurement infra v1.3: websocket node/step timing, true VRAM peak,
manifest-driven variants, full server lifecycle per variant, quality gates
with determinism noise floor (0.0000). User verdicts RECORDED (turbo×3+ck 无感, w4a8 略降→rejected, 2048 praised);
AI second opinion (GLM-5.3-Flash) dual-confirmed: 5/5 match + 3 first
verdicts, 0 divergence >=1 grade (558ed07). Recommended configs final.

