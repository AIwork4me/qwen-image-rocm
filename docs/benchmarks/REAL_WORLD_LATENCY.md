# Real-world latency: unified cold-start vocabulary

Warm steady-state throughput (e.g. "9 s/image") is a *benchmark* number.
A user's actual wait depends on cache state. This page separates the
scenarios and never mixes them. All rows: RX 7900 XTX, Windows 11,
torch 2.12.0+rocm7.14.1, ComfyUI pinned commit, euler/simple, cfg 1.0 —
environment evidence `bench/results/env/snapshot-20261101-141420.json`.

**The four metrics (exact definitions — used everywhere in this repo):**

| Metric | Definition |
|---|---|
| **Server boot** | server process launch → `/system_stats` reports a healthy Radeon device |
| **Ready-to-first-image** | server healthy → first PNG on disk (includes model load + cold text-encode) |
| **Full cold start** | process launch → first PNG on disk = Server boot + Ready-to-first-image. Ready-to-first must NEVER be quoted as "cold start" on its own |
| **Warm mean / median** | same prompt, new seed, models resident, text-encode a node-cache hit; mean and median over the measured runs |

Plus **Fresh prompt** = warm server, prompt *text* changed (text encoder
recomputed; verified by `text_encode_s > 0` and `CLIPTextEncode` absent
from `cached_nodes`).

## Fast profile — SHIPPED DEFAULT (E8 config: turbo int8 DiT + **bf16 TE** + ck)

The #5 owner verdict (2026-11-01) rejected the int8-TE triple as the Fast
default (p1 略降, p3 typography 不可接受); Fast ships E8. Measured 2026-11-01
(post-verdict regression run, `bench/results/quickstart/` local run,
records gitignored by design; digests verified incl. the 17.5 GB bf16 TE):

| Metric | Value |
|---|---|
| Server boot | 18.2 s (bf16 TE scan) |
| Ready-to-first-image | 32.6 s (cold TE 7.16 s + 17.5 GB TE/DiT load) |
| **Full cold start** | **50.8 s** |
| Warm mean / median | 9.18 / 9.07 s (n=2; matches the e8 experiment's 9.1 s) |
| Fresh prompt | warm + 3–7 s bf16 TE recompute (phase-3 measured band; no fresh arm re-run for E8 — labeled estimate, source cited) |
| 2048² | e2 probe 42.2 s warm (turbo-int8 + bf16 TE family — same TE as the default; triple-config r3 matrix below is variant evidence) |

## Fast profile — VARIANT (int8-TE "production triple"; owner-rejected as default, kept as evidence)

| Metric | Warm-cache host | Fresh-install clone (clean-dir acceptance) | Source (records) |
|---|---|---|---|
| Server boot | 8.1 s | **28.3 s** | quickstart timers (boot benefits from OS file cache on the bench host; the clone number is the honest provisioning-fresh one) |
| Ready-to-first-image | **12.1 s** (TE 2.37 · load+denoise · VAE 0.92) | **17.2 s** (TE 5.03 — cold-cache text encode) | cold records: `quickstart-Fast-20261101-142448/`, clone acceptance run; colder session r1 cold = 17.1 s |
| **Full cold start** | **20.2 s** | **45.5 s** | sum of the two rows above; a rebooted machine (cold disk cache) is **NOT TESTED** — expect worse |
| Fresh prompt | **10.0–10.1 s** (real int8 TE 1.22–1.24 s, n=3 prompts) | not measured on clone | `2026-11-01-r1-triple/` fresh-prompt arm |
| Warm | **mean 8.11 s** (dev run) / medians 8.30/9.06/8.09 s (n=9) | mean 8.57 s (clone) | r1-triple + quickstart runs |
| Total wall, launch → 4 images | 48.1 s | 73.9 s | script timers |
| One-time (ever) | weight download ~18 GB (Fast set) | idem | `docs/weights.md`; resumable, not timed here |

## Fast profile at 2048² (`-Mode Fast -Resolution 2048`)

| Metric | Value | Source | Notes |
|---|---|---|---|
| Ready-to-first-image | 43.3 s (TE 2.29 · KSampler 36.5 · VAE 2.85) | `2026-11-01-r2-2048fast/` cold | triple config; boot not timed on that run → Full cold start N/A, not guessed |
| Warm | 40.2–40.3 s | same, warmup+measure | probe tier — see 2048_VALIDATION.md |

## Quality profile (`-Mode Quality`, 1024², bf16, 40 steps)

| Metric | Value | Source | Notes |
|---|---|---|---|
| Server boot | 8.1 s | script timer | warm OS cache |
| Ready-to-first-image | **59.4 s** (TE 7.46 · KSampler+load 49.7 · VAE 1.22) | `quickstart-Quality-20261101-142606/` cold | 31.8 GB of bf16 weights on a 32 GB-RAM host |
| **Full cold start** | **67.5 s** | sum | — |
| Warm | mean 46.4 s / median 46.3 s (n=2); historical band 45–51 s ✓ | same run + `2026-10-31-e1-control` | — |
| Total wall, launch → 4 images | 208.5 s | script timer | — |
| Fresh prompt | TE 3–7.5 s on top of warm | phase-3 + this run's cold TE | plus model-swap cost under RAM pressure |

## Measurement semantics & limitations (read before quoting)

- **VRAM numbers are sampled** (`/system_stats` polled every 0.5 s): they
  are *Sampled System VRAM Usage* — lower bounds that can miss short
  transient allocation peaks. PyTorch allocator peaks are not captured;
  `vram_residency_mb` in the records is a different quantity (model
  residency). No number here claims to be the true instantaneous peak.
- **Per-step arrays are partial for non-measured records** (step-times
  audit, 2026-11-01): in monitor-era records the step-1 websocket event is
  frequently lost and some cold records have no step events (105/337
  records carry `step_times_s` shorter than `steps`). No published number
  in this repo derives from those arrays — totals and node timings
  (`total_s`, `ksampler_s`, `text_encode_s`, `vae_decode_s`) are
  server-authoritative. Audit tool: `python -I tools/check_step_times.py`.
- Host RAM: not instrumented in these runs → **N/A**, not 0.
- Cache-hit counts come from ComfyUI's node cache report per record
  (`cached_nodes`); warm rows are exactly the cache-hit case.
- Cold rows on the bench host had a warm OS file cache; a rebooted
  machine's first cold start will be slower (disk-bound). Labelled above;
  bounded reboot measurement **not run**.
- `MB` in records follows ComfyUI's own reporting convention (2²⁰-based);
  treat GB figures as approximate.
- Timer source: driver wall clock (`total_s` per record) + PowerShell
  timers for boot phases; run counts and min/median/max per scenario are in
  the cited record files (JSON, schema-validated).

## How to reproduce each row

```powershell
.\quickstart.ps1 -Mode Fast                    # prints boot / ready-to-first / full-cold / warm mean+median
.\quickstart.ps1 -Mode Fast -Resolution 2048
.\quickstart.ps1 -Mode Quality
# protocol-grade fresh-prompt arms (n=3 prompts, records):
powershell -File bench\run_variant.ps1 -Experiment p3-turbo-int8-ck-te-nosmart-1024x1024 -Date <tag>
```
