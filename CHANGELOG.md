# Changelog

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

