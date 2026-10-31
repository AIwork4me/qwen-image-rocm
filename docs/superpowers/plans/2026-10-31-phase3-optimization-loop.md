# qwen-image-rocm Phase 3: Optimization Loop — Implementation Plan (v2)

> **For agentic workers:** execute task-by-task; steps use checkbox (`- [ ]`) syntax.
> **Execution rule (user, 2026-10-31):** run the WHOLE plan in one go — do not
> stop after the tooling tasks. Collect user quality-verdict evidence in batches.

**Goal:** run the design-doc Phase 3 optimization loop — each experiment = one
variable + speed measurement + quality comparison, all paired against a bf16
baseline — through levers Turbo / native quantization / attention backends /
torch.compile / VAE tiling / VRAM-cache modes, ending with a cross-experiment
summary and a recommended 1024² production config.

**Spec:** `docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md` (Phase 3
section + 基准协议 + 画质门槛协议 + 公平对比规则).

**Two-round review corrections baked into this plan (2026-10-31):**

1. **No fp8 exists for Qwen-Image-2.1** (hf-mirror tree of Comfy-Org/Qwen-Image-2.1:
   DiT = bf16 / int8_convrot / turbo_bf16 / turbo_int8_convrot; TE = bf16 /
   int8_convrot / w4a8). On gfx1100 fp8 would be emulated anyway
   (`model_management.py:536-541`); int8 is native on HIP. Native quantized
   checkpoints load via plain `UNETLoader` (`weight_dtype: default`, metadata
   detection in `comfy/utils.py:1467`) — zero custom nodes, zero venv changes.
   E2 is therefore "native int8/w4a8 matrix", not "fp8".
2. **E4 attention semantics:** `--use-pytorch-cross-attention` force-re-enables
   flash+mem-efficient+math (`model_management.py:547-550`), silently undoing the
   wrapper's math-only workaround → needs a "math-hard" wrapper mode that neuters
   re-enables. Real matrix: default(sub-quadratic) / -NoMath / --use-split /
   --use-quad / --use-ck-attention / pytorch+math-hard / pytorch+aotriton env.
   `attention_backend` is asserted from the SERVER LOG, never assumed from flags.
3. **Measured-run cache truth:** ComfyUI caches per-node outputs by input hash;
   measured runs differ from warmup only by seed, so CLIPTextEncode is a cache
   hit and the 45–51 s baseline EXCLUDES text encode (report.md limitation text
   was wrong). Phase 3 adds websocket node/step timing + a fresh-prompt arm so
   TE cost becomes visible — mandatory before Turbo claims (TE dominates there).

Methodology upgrades: same-session bf16 shadow control (all speedups are
same-session paired ratios); per-prompt medians; explicit MDE (~10% at n=3);
n=5 for small-effect experiments (E6/E7); outlier rule (range > 5% of median →
+2 runs); screening numbers (n=1) never enter summary tables. Protocol → v1.3
(warmup seed +2e6 so warmups actually execute; cold stays +1e6).

## Global Constraints

- Baseline venvs frozen; baseline behavior byte-identical (CI-guarded via a
  manifest-reproduces-phase-2 test). Phase-3 variants are data (manifests), not
  code forks.
- Weights: ModelScope-first; Comfy-Org via hf-mirror per `docs/weights.md`
  procedure (`HF_HUB_DISABLE_XET=1` + stall watchdog). GGUF is demoted to an
  optional appendix (isolated venv copy + external custom_nodes yaml) — native
  quant is strictly better on this stack (`main.py:679-686` deprecation).
- Every variant runs on a freshly started server (run_variant.ps1 lifecycle:
  start → 7900 health gate → driver → POST /free → kill tree → port-free check).
  Probes that OOM mark the variant `blocked` and force a restart.
- Result JSONs validate against the schema before writing; new optional fields
  (cfg, unet/clip/vae, ksampler_s, vram_residency_mb, cached_nodes,
  session_id/restart_idx) make every run self-describing.
- Image evidence ≤100MB per push; grids + curated samples only.
- Commit per task/experiment; push with retries (github flaky). Deviation from
  the spec's "short-lived branch" rule (direct-to-main with defaults-frozen
  guard) is recorded here.

## Task 0 — this document
- [x] Write + commit this plan.

## Task 1 — Measurement infrastructure (protocol v1.3)

- [ ] `bench/core.py`: warmup seed = seeds[0]+2_000_000 (cold stays +1e6);
      docstring + tests updated.
- [ ] `bench/comfyui_client.py`: `RunMonitor` — websocket listener
      (`/ws?client_id=...`, websocket-client dep via `uv run --with`) capturing
      `executing` (per-node) and `progress` (per-step) events with perf_counter
      timestamps; VRAM sampler thread polling `/system_stats` at 0.5 s
      (max → `vram_peak_mb`, final → `vram_residency_mb`); `summarize(workflow)`
      → node durations (class-resolved), `text_encode_s`, `vae_decode_s`,
      `ksampler_s`, `step_times_s`, `cached_nodes`.
- [ ] `bench/experiments.py` + `bench/experiments/*.json`: manifest loader +
      validation; `p2-comfyui-1024x1024.json` reproduces Phase 2 exactly
      (guarded by a test); manifests for control/turbo/int8×/vaetiled/attn×/
      vram× variants.
- [ ] `bench/run_comfyui.py`: `--experiment <manifest>` single entry
      (default = p2 manifest → old behavior); build_record derives all fields
      from manifest+spec; optional fresh-prompt arm (`fresh_prompt_arm` in
      manifest; run_kind `fresh_prompt`; prompt text + " ." to bust the TE
      node cache).
- [ ] Schema: runs.kind += "fresh"; run_kind += "fresh_prompt"; new optional
      properties (above).
- [ ] `phase2-comfyui/launch_wrapper.py`: `QIR_SDP=math-hard` mode (disables
      accelerated SDPA pre-import AND neuters later `enable_*_sdp(True)` calls).
- [ ] `phase2-comfyui/launch_comfyui.ps1`: `-ComfyArgs` passthrough, `-SdpMode`.
- [ ] `bench/run_variant.ps1`: full server lifecycle per variant (above).
- [ ] `bench/make_report.py`: v1.3 + TE-cache correction in Limitations.
- [ ] Tests: update test_core/test_run_comfyui/test_comfyui_client; new
      test_experiments; all CPU-only; ruff clean; CI green.

## Task 2 — Quality gate tooling

- [ ] `bench/quality_gate.py`: paired grid (per prompt: [base|exp]×3 seeds at
      256px) + poster native-res 512² crop strips; LPIPS(alex) per pair with
      per-prompt medians; semantics split (fidelity for same-model variants vs
      distance-not-quality for Turbo); noise-floor option (same-config rerun
      pair); emits quality.md with three-tier verdict slot (无感/略降/不可接受,
      user final).
- [ ] `phase3-quality/` uv venv (PyPI CPU torch + lpips + pillow + numpy);
      LPIPS weights (alex linear + alexnet backbone) pre-fetched into the torch
      hub cache (github-flaky network); identical-image sanity check ≈ 0.
- [ ] `tests/test_quality_gate.py` (mocked lpips).

## Experiments (each: same-session control → restart → variant → schema/report/
grid/LPIPS → user verdict batch → commit)

- [ ] **E1 Turbo** `p3-turbo-8step-1024x1024`: turbo_bf16 DiT, 8 steps official
      template; fresh-prompt arm ON; end-to-end claims only, step-count labeled.
- [ ] **E2 native quant matrix**: `p3-int8-dit`, `p3-int8-te`, `p3-w4a8-te`,
      `p3-int8-dit-te`, `p3-turbo-int8`; capture server "Native ops:" log line;
      2048² feasibility probe per promising combo (blocked = recorded data).
- [ ] **E3 GGUF appendix** (only if time; isolated venv copy + external
      custom_nodes; conclusion scoped to deprecated loader path).
- [ ] **E4 attention matrix**: default / -NoMath / split / quad / ck-attention /
      pytorch+math-hard / pytorch+aotriton-env; backend asserted from server log.
- [ ] **E5 torch.compile** (diffusers): QIR_COMPILE=1; record exact failure
      signature; extend docs/issues/2026-10-30-no-triton-windows-rocm.md.
- [ ] **E6 VAE tiling** `p3-vaetiled` (n=5; node timing + true VRAM peak).
- [ ] **E7 VRAM/cache modes**: default vs --highvram / --disable-smart-memory /
      cache-none / --fast fp16_accumulation (n=5; probes for expected failures;
      no-op flags documented not run).
- [ ] **E8 open slot**: step-distill LoRAs (`p_q_image_2.1_{5,6,8}_steps`),
      UNETLoader on-the-fly fp8 (emulated, contrast cell), TE residency, other.

## Summary
- [ ] `bench/results/<date>-phase3-summary/report.md`: same-session paired
      ratios, VRAM peak/residency, LPIPS (split semantics), verdicts, MDE notes,
      recommended 1024² config.
- [ ] README EN+zh Phase 3 sections + TE-cache baseline correction; CHANGELOG;
      docs/weights.md additions; push everything.

## Verification
- [ ] pytest + ruff + CI green after every task; manifests reproduce Phase 2.
- [ ] Shadow control drift > 5% vs last session → stop and investigate.
- [ ] Every experiment dir: schema-valid JSONs, report.md, quality_grid.png,
      quality.md, server attention evidence.
