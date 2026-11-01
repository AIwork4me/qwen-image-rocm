# qwen-image-rocm Phase 4: RCA Verification + Upstream Contribution Track — Implementation Plan

> **For agentic workers:** execute task-by-task (`- [ ]` checkboxes). **Execution
> rule (user, 2026-11-01):** run the WHOLE plan in one go; batch user-gated
> decisions (upstream posts) at natural milestones.
> **Handoff note:** this plan is self-contained — all intel needed is in the
> annexes below. Written 2026-11-01 after two research agents (repo + web);
> not yet executed.

**Goal:** verify the (now upstream-root-caused) cause of finding #1 on this
machine, measure what the fixed builds buy us, and contribute the missing
gfx1100/whl-multi-arch data points upstream — plus the queued quick wins
(findings #4/#5, hf resume, comfy-kitchen perf data).

**Spec:** `docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md`
(Phase 4 section). Entry condition "Phase 3 数据全部到手" is MET (quality gate
dual-confirmed 2026-11-01, commit 558ed07+).

## Why this plan differs from the original Phase 4 sketch

Upstream research (2026-11-01, primary sources fetched directly) found
finding #1 is **already root-caused upstream** — an AOTriton runtime/images
version mismatch in the torch 2.12.0+rocm7.14.1 Windows wheel lineage, with
fixes merged to pytorch release/2.11 & 2.12 and a same-index good build
(+rocm7.14.0) available. Details + links: **Annex A**. Therefore:

- NO deep unknown-bug RCA; we VERIFY the known cause locally and measure.
- NO WSL2 comparison (dropped — cross-OS isolation adds nothing now).
- NO new PyTorch/TheRock issue (dedup rule) — the contribution is the
  missing **gfx1100 + repo.amd.com/whl-multi-arch + 2.12.0+rocm7.14.1** data
  point on the OPEN issues, with a standalone repro.

## Global Constraints (unchanged from design doc)

- Baseline venvs (`phase1-diffusers`, `phase2-comfyui`) NEVER touched.
  Non-mandated torch goes ONLY into one-shot diagnostic venvs
  (`phase4-diag-*`, gitignored).
- Upstream actions (comments/issues/PRs) are outward-facing: drafts land in
  `docs/upstream/`, and NOTHING is posted until the user approves each item
  (user may post personally — AMD employee identity).
- Commit+push per milestone; push retries (github flaky); pytest/ruff green.

---

## W1. Minimal repro: `tools/repro/sdpa_repro.py` (committed, no model weights needed)

Sweep matrix (recipe from repo exploration, Annex B):
- tensors `(B,H,S,D)` = (1, 32, S, 128) bf16; S ∈ {64, 256, 1024, 4096
  (≈1024² DiT), 16384 (≈2048² DiT)} + one TE-realistic seq (~120)
- GQA on/off (KV heads 8 vs 32 — TE is GQA 32Q/8KV, DiT is full 32/32)
- mask ∈ {None, bool-4D, float-additive} × is_causal {True, False}
- backends via `torch.nn.attention.sdpa_kernel(SDPBackend.FLASH_ATTENTION |
  EFFICIENT_ATTENTION | MATH)`
- error flushing ComfyUI-style (model_management.py:497-527 pattern):
  launch → `torch.cuda.synchronize()` → `torch.zeros(1).add_(1).item()`
- ALSO inspect the installed wheel's aotriton evidence: presence/version
  strings in `torch/lib/` (`aotriton.images`, `aotriton_v2.dll`) vs the
  mismatch pattern in TheRock#7315 (0.12 pin vs 0.13 images)
- output: pass/fail matrix → `docs/issues/evidence/sdpa-repro-matrix.md`
  + update finding-1 doc
- expected on current stack: flash/mem-eff ALL RED (any shape), math GREEN

- [ ] script + matrix on current stack (phase1 venv python, GPU)
- [ ] aotriton wheel-inspection evidence recorded
- [ ] commit

## W2. Diagnostic venv: torch 2.12.0+rocm7.14.0 verification

- [ ] `uv venv phase4-diag-7140/.venv` + install from the SAME mandated
      index `https://repo.amd.com/rocm/whl-multi-arch/`:
      `torch[device-gfx1100]==2.12.0+rocm7.14.0` (+torchvision matching)
      — win_amd64 build VERIFIED to exist on that index (Annex A.4)
- [ ] run W1 repro in it → expect flash/eff GREEN (if still red: that IS the
      data point for #7315 — record and proceed)
- [ ] if green: quick benefit measurement (single p1 1024² generations via
      `phase1-diffusers/generate.py` copied invocation or minimal script):
      math vs flash s/step + VRAM; one 2048² probe (mem-efficient avoids the
      32.1GB dense alloc → bf16 2048² may unlock)
- [ ] stretch (optional, network permitting): `phase4-diag-next/.venv` from
      `https://nightly.repo.amd.com/rocm/whl-next/` with
      `"torch[device-gfx1100]"` (2.13.0+rocm10.2 line verified) → repro
      matrix + try `pip install triton` there (Annex A.3: no public Windows
      triton today; if the whl-next stack ships one, capture flex/compile
      numbers = finding #3's final answer)
- [ ] extend `tools/snapshot_env.py`: transformers/diffusers versions +
      per-backend SDPA probe result; +CPU tests for the new fields
- [ ] commit (snapshots + results; venvs stay gitignored)

## W3. Upstream contribution drafts — `docs/upstream/` (ALL user-gated)

1. **TheRock#7315 comment** (core): gfx1100 + whl-multi-arch +
   2.12.0+rocm7.14.1 data point; W1 repro script + failure matrix; (if W2
   green) 7.14.0 all-green contrast; reference #7992; note the stable
   channel still shipping the known-broken build (channel hygiene).
   Optional cross-comment on ROCm/aotriton#210.
2. **transformers/diffusers PR draft** (finding #5): SDPA probe+fallback or
   actionable error translation for `hipErrorInvalidValue` ("disable
   flash/mem-efficient SDPA"), citing the ComfyUI probe contrast
   (model_management.py:497-527) and #7315 root cause.
3. **accelerate issue draft** (finding #4): pagefile-thrash quantified data
   (6× step time, self-recovers; 31.8GB RAM vs 30.9GB weights).
4. **huggingface_hub#4196 comment draft**: our measured ~30GB duplicate
   downloads (parallel chunks never resume after kill) +
   `tools/download_parallel.py` as a community workaround.
5. **comfy-kitchen perf data point** (issue/discussion draft): Windows
   RDNA3 has no public ck benchmark; our 1.30–1.37× at 1024² (+ protocol);
   note AMD's Linux CK blog shows +31.6–36.4% (different implementation —
   composable_kernel vs Comfy Kitchen HIP int8).
6. Optional backlog (only if time): ComfyUI draft notes for
   VAEDecodeTiled residency thrash (5× slower) and
   `--fast fp16_accumulation` long-text 0.22× pathology.

- [ ] all drafts in `docs/upstream/` with per-item submit-channel notes
- [ ] present a one-page approval list to the user; post ONLY approved
      items (user posts personally or authorizes gh submission)
- [ ] record posted links back into the drafts + issue docs; commit

## W4. Documentation closeout

- [ ] finding-1 doc: root-cause section (upstream refs + our local aotriton
      evidence + W2 result) + the three remediation paths (disable backends
      / downgrade 7.14.0 / whl-next nightly) with measured costs
- [ ] finding-3 doc: verified Triton-on-Windows status (TheRock PR#4006
      merged but no public wheels; no path for 2.12+7.14.1) + W2-stretch
      measurements if any
- [ ] README zh/en "ROCm findings": #1 recast as "upstream-root-caused,
      verified locally, remediation measured"; CHANGELOG entry; `patches/`
      not created (fixes live in upstream versions, not local patches —
      document this ruling)
- [ ] if W2 shows flash meaningfully faster: produce a stack-switch decision
      sheet for the user (do NOT change the mandated baseline unilaterally)
- [ ] final commit + push + memory update

## Verification

- W1: expected red/green matrix on current stack; wheel-inspection evidence
- W2: 7.14.0 matrix green (or recorded red — also valuable)
- tests: 43+ green throughout (only tools/ + snapshot additions; add CPU
  tests for new snapshot fields)
- W3: drafts pushed; NOTHING posted without explicit user approval

---

## Annex A. Upstream intel (verified 2026-11-01 unless marked)

1. **TheRock#7315** (OPEN, 2026-08-12) "[Windows] SDPA FLASH/EFFICIENT fail
   with hipErrorInvalidValue" — gfx1201 primary, **confirmed gfx1151 and
   gfx1101**. Root cause: AOTriton runtime/images version mismatch (pytorch
   pinned `__AOTRITON_CI_COMMIT` to a 0.12 commit; shipped 0.13 images;
   older 0.12 resolved images via `dladdr` — non-Windows API). Fixes: pytorch
   release/2.11 c9ab269, release/2.12 d1abf10; ROCm/pytorch#3569 (merged),
   #3568 (open). https://github.com/ROCm/TheRock/issues/7315
2. **TheRock#7992** (CLOSED 2026-09-15) — torch **2.12.0+rocm7.14.1** and
   +rocm10.0.0 broken after any SDPA call; **+rocm7.14.0 fine**; HIP/AOTriton
   hash version mismatch (build issue); fixed nightlies on
   nightly.repo.amd.com; reporter confirmed 2.15.0a0+rocm10.1.0 passes.
   Workarounds identical to ours (enable_flash_sdp(False) etc.).
   https://github.com/ROCm/TheRock/issues/7992
3. **Triton on Windows**: triton-lang/triton-windows (AMD RDNA2/3/3.5/4
   supported but requires TheRock-matched builds; import-order caveat
   issue #35). TheRock PR#4006 "triton-windows integration" merged
   2026-03-23 (wheels built in TheRock pipeline, `--pytorch-rocm-arch
   gfx1100` tested) — **not on a public index yet**. AMD's
   nightly.repo.amd.com triton 3.8.0 wheels: **Linux only**. Old
   rocm.nightlies.amd.com/v2 gfx110X-dgpu: stale (2025-11-20), no triton.
   ⇒ no pip-installable Triton for torch 2.12.0+rocm7.14.1 native Windows.
4. **Wheel availability (direct index fetches)**: whl-multi-arch has
   torch **2.12.0+rocm7.14.0 win_amd64** (the good build) and 2.13.0 only
   for Linux. whl-next (`https://nightly.repo.amd.com/rocm/whl-next/`) has
   torch 2.12.0 and **2.13.0+rocm10.2.0a*** win_amd64; install format
   `pip install --index-url .../whl-next/ "torch[device-gfx1100]"`.
5. **aotriton in Windows wheels**: shipped inside the torch wheel
   (`torch/lib/aotriton.images` + `aotriton_v2.dll`), enabled via TheRock
   PR#1437 (2025-09). Known Windows issues: the mismatch family above;
   TheRock#1315 (Triton codegen gfx1100 accuracy); aotriton#184 (wide-path).
6. **hf resume**: huggingface_hub#4196 (OPEN, bug) — since PR#4306 partials
   are `{etag}.{uuid4}.incomplete`, resume never invoked; maintainer defers
   the real fix to xet-core#989.
   https://github.com/huggingface/huggingface_hub/issues/4196
7. **comfy-kitchen** ("ck" = Comfy Kitchen, NOT composable_kernel): external
   wheel with precompiled HIP backends (RDNA2/3/3.5/4, Windows HIP builds);
   PyPI wheels lack the HIP backend (CI artifacts only); issue#110 AMD crash
   fixed in 7c6ca3a (reporter saw ~2×). No public Windows/RDNA3 benchmark.
   AMD blog (Linux, composable_kernel, WAN2.2): +31.6–36.4% vs AOTriton SDPA
   on Navi31 — matches our 1.30–1.37× numerically (different impl).
8. Unverified leads: TheRock#5543 (gfx1100 hipErrorInvalidImage, 2026-05,
   gfx110X-all nightly); aotriton#251 (gfx1201 Linux dup of #210).

## Annex B. Repro recipe inputs (from repo exploration)

- TE (Qwen3-VL 8B): H=32, D=128 (head_dim), KV heads 8 (GQA), causal,
  36 layers, bf16; sdpa call: `transformers/integrations/sdpa_attention.py:174-183`
  on (B,H,S,D); plain prompts pass attention_mask=None → is_causal=True.
- DiT (QwenImage21): H=32, D=128, full attention (no GQA), 32 layers, bf16;
  prefill builds **bool 4D segment masks** (diffusers
  `transformer_qwenimage21.py:514-520`), call via
  `diffusers/models/attention_dispatch.py:3760` (native SDPA); decode path
  mask=None.
- Prompt seq lens are SHORT (57/141/73 chars) — TE fails at small S too, so
  small-S repro should suffice for TE; DiT needs S≈4096 (1024²).
- ComfyUI probe pattern (the thing that saves ComfyUI):
  `phase2-comfyui/ComfyUI/comfy/model_management.py:497-527` —
  probe SDPAParams, launch under sdpa_kernel(FLASH), synchronize, dummy
  add to flush async error, catch → disable.
- ck works because comfy_kitchen's own HIP kernels bypass torch SDPA
  dispatch entirely (independent evidence the GPU/shapes are fine).
- Existing repro-ish assets: `docs/issues/evidence/sdpa-attempt-{a..e}.log`,
  `tools/compile_probe.py` (finding-1 masking lesson: apply the math
  workaround BEFORE probing compile).
- Env snapshot to extend: `tools/snapshot_env.py` (9 fields; add
  transformers/diffusers versions + SDPA backend probe results).
