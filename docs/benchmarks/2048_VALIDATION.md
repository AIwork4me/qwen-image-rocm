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
| Turbo-int8 8-step, p1 (zh scene), seed 42 | single probe (cold+warmup+n=1) | 2026-11-01 (phase 3) | `bench/results/2026-11-01-e2-turbo-int8-2048-probe/` | warm 42.2 s · cold 91.5 s · sampled VRAM 21.6/12.0 GB |
| int8 DiT+TE 40-step, p1, seed 42 | single probe (n=1) | 2026-11-01 (phase 3) | `bench/results/2026-11-01-e2-int8-dit-te-2048-probe/` | warm 328.3 s · cold 332.3 s · sampled VRAM 20.1/16.7 GB |
| **Fast profile (full triple), p2 (en scene), seed 42** | single probe (cold+warmup+n=1), different session AND different prompt than the turbo probe above | 2026-11-01 (this session) | `bench/results/2026-11-01-r2-2048fast/` | warm 40.2 s · cold 43.3 s (incl. load) · sampled VRAM ≈ 8.3 GB |
| Cross-session/cross-prompt consistency | implied by the two turbo probes (42.2 vs 40.2 s) | — | above two rows | Δ ≈ 5% |

## What is NOT yet validated (explicitly)

- **Multi-seed repeats** at 2048² (n=1 per scenario measured to date).
- **Multi-prompt coverage within one session** (p1 and p2 each have exactly
  one probe; p3 — the long-text poster, the hardest resolution case — has
  **zero** 2048² runs).
- **Fresh-prompt switching** at 2048² (no measured TE-recompute arm).
- **Long continuous runs** (no >3-image session at 2048²).
- **OOM recovery** (no deliberate pressure/recovery test).
- **Bounded cost of closing these gaps** (estimate): a 3-prompt × 3-seed
  Fast-profile 2048² matrix ≈ 9 × ~41 s + 2 model-reload colds ≈ **~15 min
  GPU**; not executed in this session to keep the release-candidate scope
  bounded. Owners can run it with:
  `powershell -File bench\run_variant.ps1 -Experiment p4-qs-fast-1024x1024 -Date <tag> -Resolution 2048 -Measured 3`
  (the manifest carries the full triple config).

## VRAM statement semantics

All GB numbers above are **sampled** `/system_stats` polls (0.5 s) — lower
bounds on transients, not PyTorch allocator peaks. The int8 route's ~8–12 GB
sampled peaks leave real headroom on 24 GB; the 40-step route samples up to
~20 GB and is the closer call.

## Allowed vs not-allowed wording

- ✅ "2048² native generation demonstrated and re-probed across two sessions
  and two prompts: ~40–42 s/image (turbo int8, 8 steps), ~328 s (int8,
  40 steps)"
- ✅ "quickstart: `.\quickstart.ps1 -Mode Fast -Resolution 2048`"
- ❌ "2048² validated / production-stable / hours of continuous use"
- ❌ extrapolating the 1024² 5.2–5.5× ratio to 2048² (different bottleneck
  mix; only the probe times themselves are quotable)
