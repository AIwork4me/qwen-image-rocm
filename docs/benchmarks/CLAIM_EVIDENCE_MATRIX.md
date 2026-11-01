# Claim → evidence matrix

Every performance or capability claim this repo makes in public-facing text
(README, release notes, social assets) must resolve to a row here. Statuses:

- **MEASURED** — a recorded run exists; numbers quoted match the raw record.
- **MEASURED (this session)** — recorded 2026-11-01 (release-readiness
  session), records committed alongside this doc.
- **PROBED** — one recorded run (single seed/prompt); capability
  demonstrated, stability not claimed.
- **HISTORICAL** — recorded in an earlier session; kept read-only.
- **PROJECTED** — arithmetic over separate measurements; never presented as
  a measured combination.
- **UNVERIFIED / BLOCKED** — no acceptable evidence; must not be claimed.

Rules: ratios from *different* experiments are never multiplied into a
"combined speedup". Warm numbers are never presented as end-to-end user
latency (see REAL_WORLD_LATENCY.md). LPIPS never appears without its
semantics label (fidelity vs distance).

## Common environment (all rows unless noted)

RX 7900 XTX (gfx1100, 24 GB) · Windows 11 native · Adrenalin driver
32.0.21030.2001 · torch `2.12.0+rocm7.14.1` (AMD wheel index) + HIP
7.14.60850 · CPython 3.12.16 · transformers 5.22.1 · ComfyUI pinned commit
`b5a43215` — evidence: `bench/results/env/snapshot-20261101-141420.json`
(includes per-backend SDPA probe: flash/mem-eff/cudnn FAIL, math PASS on
this build — finding 1). Model identity: `Comfy-Org/Qwen-Image-2.1`
checkpoints (bf16 / int8_convrot / turbo / turbo_int8_convrot; exact byte
sizes in `bench/quickstart_config.py`; sha256 verified against the host's
LFS pointer by `quickstart.ps1`). Protocol: `bench/prompts.json` (3 frozen
prompts, seeds 42/1337/20261030, cold/warmup seeds +1e6/+2e6), euler/simple,
cfg 1.0. Records are schema-validated (`bench/schema/result.schema.json`).

## Matrix

| # | Claim (exact wording allowed in public text) | Status | Evidence |
|---|---|---|---|
| C1 | "1024² warm: 9.1 s/image, 5.2–5.5× vs same-session bf16-40 control" | MEASURED (session e1, HISTORICAL) | `p3-turbo-int8-ck-1024x1024` → `bench/results/2026-11-01-e8-turbo-int8-ck/` (n=9, per-prompt medians 9.1/9.1/9.1 s; paired vs `2026-10-31-e1-control` 48.2/50.2/48.4 s). Warm = same prompt, TE cached (`cached_nodes` shows `CLIPTextEncode`). |
| C2 | "Recommended production combo (turbo int8 DiT + int8 TE + ck + `--disable-smart-memory`) measured as a whole: 8.0–9.2 s warm at 1024²" | MEASURED (this session) | `p3-turbo-int8-ck-te-nosmart-1024x1024` → `bench/results/2026-11-01-r1-triple/` (n=9; medians 8.30/9.06/8.09 s; fresh-prompt arm 10.0–10.1 s incl. 1.2 s real int8 TE; cold 17.1 s). Speed class equals C1; cross-session ratio vs e1 control ≈ 5.5–6.0× is context only, **not** a same-session paired claim. |
| C3 | "2048² native: 40.24–40.45 s/image with the Fast profile (turbo int8, 8 steps) — bounded matrix, 3 prompts × 3 seeds" | **MEASURED (bounded matrix, this revision)** + 2 historical probes | `2026-11-01-r3-2048matrix/` (n=9, medians 40.27/40.32/40.36 s incl. first-ever p3 typography runs, in-session prompt switching, spread 0.5%, cold 47.5 s, sampled VRAM 8.3–12.6 GB, fresh-TE 1.28–1.31 s). Historical: e2 probe 42.2 s (p1), r2 probe 40.2 s (p2). Still NOT claimed: soak/OOM-recovery (2048_VALIDATION.md). |
| C4 | "2048² int8 40-step route: 328 s" | PROBED (HISTORICAL) | `2026-11-01-e2-int8-dit-te-2048-probe/` (n=1). |
| C5 | "bf16-40 ComfyUI baseline: 45–51 s warm (1024²); diffusers+cpu_offload: 239–254 s" | MEASURED (HISTORICAL) | Phase 1/2 reports `2026-10-31-math-1024/`, `flex-1024/`, `comfyui-1024/` (n=3/prompt). |
| C6 | "`--use-ck-attention` is the only faster attention backend on gfx1100 here: 1.30–1.37× at 1024²" | MEASURED (HISTORICAL) + upstream posted | `p3-attn-ck-1024x1024` → `2026-11-01-e4-ck/` (n=9; numerics path differs — LPIPS semantics distance, grid-verdict 无感 A4). Posted as comfy-kitchen#292. |
| C7 | "Native int8 DiT/TE quantization is near-lossless (LPIPS fidelity 0.004–0.060; user verdict 无感)" | MEASURED (HISTORICAL) + re-confirmed this session | Phase 3: `2026-11-01-e2-int8-{dit,te,dit-te}/quality.md`. This session: triple vs e8 fidelity 0.058/0.012/0.014 median (`2026-11-01-r1-triple/quality.md`, grid attached; formal user verdict on the exact triple grid PENDING). |
| C8 | "Fix for finding 1 measured: 7.14.0 flash = 1.07 s/step @1024², 3.4× vs math, −1.9 GB VRAM; 2048² then VAE-bound" | MEASURED (HISTORICAL, weights-free repro) | `docs/issues/evidence/phase4-w2-7140-verification.md`, sdpa-repro matrices; stack-switch left to the user (`docs/phase4-stack-switch-decision.md`) — the repo's default stack stays 7.14.1 + workaround. |
| C9 | "User latencies at 1024² (Fast) — unified vocabulary: Server boot / Ready-to-first-image / Full cold start / Warm mean+median" | MEASURED (this session + revision) | Server boot 8.1 s (warm cache) / 28.3 s (fresh install); Ready-to-first 12.1–17.2 s; **Full cold start 20.2–45.5 s**; warm mean 8.11–8.57 s; fresh prompt 10.0–10.1 s. Records: r1-triple + quickstart runs + clean-clone acceptance. Full table + caveats: REAL_WORLD_LATENCY.md. |
| C10 | "VRAM" | MEASURED, sampling semantics | All "VRAM peak" numbers are **sampled** `/system_stats` polls (0.5 s), i.e. lower bounds on transients; PyTorch allocator peak is not captured. Residency is a separate metric in the records (`vram_residency_mb`). MB = 10⁶ bytes? No — records use MB as 2²⁰-based MiB per ComfyUI's own reporting; treat as approximate. |
| C11 | "Quality mode output is bit-identical to the bf16 baseline" | MEASURED (HISTORICAL) | `p3-vram-nosmart-1024x1024` LPIPS 0.0000 + SHA256 equality (phase-3 gate); quickstart Quality = same manifest flags (`p4-qs-quality-1024x1024`). |
| C12 | "torch.compile / FlexAttention blocked on Windows ROCm (no Triton wheels)" | VERIFIED distribution gap (HISTORICAL) | `docs/issues/2026-10-30-no-triton-windows-rocm.md`; re-verified vs whl-next 2026-11-01 (CHANGELOG). |
| C13 | "Any-GPU / any-AMD support" | **NOT CLAIMED** | Support matrix: tested = RX 7900 XTX only; `quickstart.ps1` fail-closes on non-Radeon and requires `-AllowUntestedGpu` for other Radeon cards. |

## Forbidden framings (enforced by review)

1. "9.1 s per image" without the **warm, 1024², cached-text-encode**
   qualifiers — cold is ~2× that, fresh ~+1.2 s, first-ever run adds a
   one-time ~18–32 GB download.
2. "5.5× lossless" — the turbo/ck speedup produces *different* images
   (LPIPS distance 0.21–0.36), judged 无感 by the user on the frozen grid;
   only the int8/nosmart levers are near-lossless/bit-identical.
3. Multiplying lever ratios (e.g. ck 1.3× × turbo 5.3×) into a combined
   number — the only compound claims allowed are C2/C3-style measured wholes.
4. "2048² validated for production" — current evidence is two probes; use
   "demonstrated / re-probed, bounded validation pending".
5. "Official AMD/Qwen project" — independent community benchmark; see
   LEGAL_AND_ATTRIBUTION.md.

## Reproduction anchors

- Fast/Quality user path: `.\quickstart.ps1 -Mode Fast` / `-Mode Quality`
  (records land in `bench/results/quickstart-<mode>-<ts>/`).
- Protocol-grade: `powershell -File bench\run_variant.ps1 -Experiment
  <manifest> -Date <tag>` (fresh server per variant, health-gated on the
  7900, attention-path evidence captured from server logs).
- Phase-1 diffusers: `.\reproduce.ps1 -Quick`.
