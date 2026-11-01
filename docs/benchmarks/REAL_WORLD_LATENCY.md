# Real-world latency: cold / fresh / warm

Warm steady-state throughput (e.g. "9.1 s/image") is a *benchmark* number.
A user's actual wait depends on cache state. This page separates the three
user-facing scenarios and never mixes them. All rows: RX 7900 XTX, Windows
11, torch 2.12.0+rocm7.14.1, ComfyUI pinned commit, euler/simple, cfg 1.0 —
environment evidence `bench/results/env/snapshot-20261101-141420.json`.

**Scenario definitions**

- **Cold start** — ComfyUI launched → first image file on disk (includes
  model loading; the table also shows the server *boot* sub-phase
  separately, because `quickstart.ps1` prints both).
- **Fresh prompt** — server warm, user changes the prompt *text* (text
  encoder recomputed; node cache for `CLIPTextEncode` defeated — verified
  by `text_encode_s > 0` and `CLIPTextEncode` absent from `cached_nodes`).
- **Warm repeat** — same prompt, different seed, models resident.

## Fast profile (`.\quickstart.ps1 -Mode Fast`, 1024², 8 steps)

| Metric | Value | Source (records) | Cache state / notes |
|---|---|---|---|
| Server boot (launch → `/system_stats` healthy) | 8.1 s | `bench/results/quickstart-Fast-20261101-142448/` + script timer | weights already in OS file cache & RAM from prior session; first boot after a reboot reads ~18 GB from disk and will be slower — **not yet measured in rebooted state** |
| Cold image (healthy → 1st PNG, incl. load) | **12.1 s** (TE 2.37 · denoise+load 7.4+ · VAE 0.92) | same run, `p2-…-cold.json` | same warm-cache caveat; colder session measured 17.1 s (`2026-11-01-r1-triple/` cold record, p1) |
| Fresh prompt (warm + real int8 TE) | **10.0–10.1 s** (TE 1.22–1.24) | `2026-11-01-r1-triple/` fresh-prompt arm, n=3 prompts | models resident (17.9 GB working set); no model swap needed |
| Warm repeat | **8.0–9.2 s** (medians 8.30/9.06/8.09; quickstart avg 8.11) | `2026-11-01-r1-triple/` n=9 + quickstart run | TE is a node-cache hit (`cached=6`) — this is the 9.1 s-class headline number, correctly qualified |
| Total wall, launch → 4 images | 48.1 s | quickstart run | includes boot + cold + warmup + 2 measured |
| One-time (ever) | weight download ~18 GB (Fast set) | `docs/weights.md` | resumable; not timed here |

## Fast profile at 2048² (`-Mode Fast -Resolution 2048`)

| Metric | Value | Source | Notes |
|---|---|---|---|
| Cold image | 43.3 s (TE 2.29 · KSampler 36.5 · VAE 2.85) | `2026-11-01-r2-2048fast/` cold | triple config |
| Warm | 40.2–40.3 s | same, warmup+measure | single prompt (p2), n=1 measured — see 2048_VALIDATION.md |

## Quality profile (`-Mode Quality`, 1024², bf16, 40 steps)

Measured this session by the quickstart dogfood run
(`bench/results/quickstart-Quality-20261101-142606/`):

| Metric | Value | Source | Notes |
|---|---|---|---|
| Server boot (launch → healthy) | 8.1 s | script timer | bf16 weights in OS cache from benchmark session |
| Cold image (healthy → 1st PNG) | **59.4 s** (TE 7.46 · KSampler+load 49.7 · VAE 1.22) | `p2-…-cold.json` | 31.8 GB of bf16 weights on a 32 GB-RAM host |
| Warm repeat | **45.6–46.3 s** (avg 46.4) | warmup + 2 measures | historical band 45–51 s (`2026-10-31-e1-control`) ✓ consistent |
| Total wall, launch → 4 images | 208.5 s | script timer | includes boot + cold + warmup + 2 measured |
| Fresh prompt (bf16 TE recompute) | TE 3–7.5 s on top of warm (phase-3 + this run's cold TE) | records | plus model-swap cost when RAM-pressured (phase-3 finding) |
| One-time (ever) | weight download ~32 GB (Quality set) | `docs/weights.md` | resumable |

## Measurement semantics & limitations (read before quoting)

- **VRAM numbers are sampled** (`/system_stats` polled every 0.5 s): they
  are *Sampled System VRAM Usage* — lower bounds that can miss short
  transient allocation peaks. PyTorch allocator peaks are not captured;
  `vram_residency_mb` in the records is a different quantity (model
  residency). No number here claims to be the true instantaneous peak.
- Host RAM: not instrumented in these runs → **N/A**, not 0.
- Cache-hit counts come from ComfyUI's node cache report per record
  (`cached_nodes`); warm rows are exactly the cache-hit case.
- Cold rows above were measured on a machine whose file cache was already
  warm from the benchmark session; a rebooted machine's first cold start
  will be slower (disk-bound). Labelled above, bounded reboot measurement
  **not run** (would need a reboot mid-session).
- `MB` in records follows ComfyUI's own reporting convention (2²⁰-based);
  treat GB figures as approximate.
- Timer source: driver wall clock (`total_s` per record) + PowerShell
  timers for boot phases; run counts and min/median/max per scenario are in
  the cited record files (JSON, schema-validated).

## How to reproduce each row

```powershell
.\quickstart.ps1 -Mode Fast                    # boot + cold + warm, printed
.\quickstart.ps1 -Mode Fast -Resolution 2048   # 2048 cold + warm
.\quickstart.ps1 -Mode Quality
# protocol-grade fresh-prompt arms (n=3 prompts, records):
powershell -File bench\run_variant.ps1 -Experiment p3-turbo-int8-ck-te-nosmart-1024x1024 -Date <tag>
```
