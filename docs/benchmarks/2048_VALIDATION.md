# 2048² capability & validation status

Native-resolution (2048×2048) generation on the 24 GB RX 7900 XTX is one of
this repo's headline results. This page states exactly how much validation
stands behind it — no more.

## Why 2048² was ever "impossible"

bf16 weights (31.8 GB) + dense attention allocations > 24 GB VRAM on the
stock 7.14.1 stack → every attention backend fails (Phase 1/2, finding 2).
The unlock is the **native int8 route**: int8-convrot DiT (7.26 GB) +
int8 TE (9.35 GB) + sub-quadratic/ck attention. On the fixed 7.14.0 build
the blocker moves to bf16 **VAE decode** (20.25 GB conv allocation OOM —
`docs/issues/evidence/sdpa-7140-2048-vae-oom.log`); the measured 2048² route
stays ComfyUI + native int8.

## Evidence ledger

| Scenario | Tier | When | Evidence | Numbers |
|---|---|---|---|---|
| **Fast profile (full triple), bounded matrix: 3 prompts × 3 seeds, one session, prompt switching in-session** | **MEASURED (bounded matrix)** | 2026-11-01 (this revision, closes [#4](https://github.com/AIwork4me/qwen-image-rocm/issues/4)) | `bench/results/2026-11-01-r3-2048matrix/` (13 records: cold + 3×(warmup+3 measures)) | medians p1 40.27 / p2 40.32 / **p3 typography 40.36** s; all-measures 40.24–40.45 s (spread 0.5%); cold (incl. load) 47.5 s; sampled VRAM peak 8.3–12.6 GB; fresh-prompt TE at 2048 measured 1.28–1.31 s (warmup arms) |
| Turbo-int8 8-step, p1, seed 42 | single probe (HISTORICAL) | 2026-11-01 (phase 3) | `…-e2-turbo-int8-2048-probe/` | warm 42.2 s · cold 91.5 s · sampled VRAM 21.6/12.0 GB |
| int8 DiT+TE 40-step, p1, seed 42 | single probe (HISTORICAL) | 2026-11-01 (phase 3) | `…-e2-int8-dit-te-2048-probe/` | warm 328.3 s · cold 332.3 s · sampled VRAM 20.1/16.7 GB |
| Fast profile (full triple), p2, seed 42 | single probe (HISTORICAL) | 2026-11-01 (release session) | `…-r2-2048fast/` | warm 40.2 s · cold 43.3 s · sampled peak 8.3 GB |

Cross-session consistency: three independent sessions (42.2 / 40.2 / 40.2–40.4 s)
agree within ~5%.

## Still NOT validated (explicitly)

- **Long continuous runs / soak** (longest session = 13 consecutive 2048
  generations; no multi-hour run).
- **OOM recovery** (no deliberate pressure/recovery test).
- **Rebooted-machine cold start** at 2048 (all boots had warm OS cache).
- Formal quality gate at 2048: no bf16-2048 reference exists (it OOMs), so
  LPIPS-vs-baseline is **N/A by construction**; the p3 typography output is
  committed as a sample for eyeball review:
  [docs/gallery/fast-2048-p3-poster-seed42.png](../gallery/fast-2048-p3-poster-seed42.png)
  (provenance in the gallery dir) — 1024² gates remain the quality
  evidence base.

## VRAM statement semantics

All GB numbers are **sampled** `/system_stats` polls (0.5 s) — lower bounds
on transients, not PyTorch allocator peaks. The int8 route's ~8–12.6 GB
sampled peaks leave real headroom on 24 GB.

## Allowed vs not-allowed wording

- ✅ "2048² native: bounded matrix measured — 3 prompts × 3 seeds, medians
  40.27/40.32/40.36 s (all measures 40.24–40.45 s), plus two earlier
  single probes; ~328 s on the int8 40-step route (probe)"
- ✅ "quickstart: `.\quickstart.ps1 -Mode Fast -Resolution 2048`"
- ❌ "2048² validated for production / hours of continuous use" (soak &
  OOM-recovery untested)
- ❌ extrapolating the 1024² 5.2–5.5× ratio to 2048² (different bottleneck
  mix; only the measured 2048 numbers are quotable)
