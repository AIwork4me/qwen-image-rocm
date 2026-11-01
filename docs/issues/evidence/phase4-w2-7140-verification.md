# Phase 4 W2: torch 2.12.0+rocm7.14.0 verification + benefit measurement

Date: 2026-11-01. Venv: `phase4-diag-7140/.venv` (one-shot diagnostic,
gitignored; baseline venvs untouched). Install source: the SAME mandated
index `https://repo.amd.com/rocm/whl-multi-arch/`,
`torch[device-gfx1100]==2.12.0+rocm7.14.0` + matching torchvision
(torch git `13eab2b3ef4e03999247f063bc2dde01c94e9eaa`; aotriton.images =
`amd-gfx11xx`, `__signature__` SHA1 `dd1b68b604b5258ee7a9f7b66ad95e7a82c18065`).

## 1. Repro matrix: ZERO launch failures (vs 48 on 7.14.1)

Identical 192-cell sweep ([matrix-7140.md](sdpa-repro-matrix-7140.md),
raw JSON `sdpa-repro-7140.json`):

| backend | PASS | FAIL | OOM | note |
|---|---|---|---|---|
| flash | 24 | 24 | 0 | PASS = every unmasked cell (all S up to 16384); FAIL = explicit-mask cells, all CPU-side `No available kernel` (same as 7141 — expected) |
| mem_efficient | 24 | 24 | 0 | PASS = every MHA cell (all masks, all S); FAIL = GQA cells (expected rejection) |
| math | 40 | 0 | 8 | identical to 7141 (≤4096 PASS, 16384 OOM 32GB dense) |
| cudnn | 0 | 48 | 0 | not built (same as 7141) |

**`hipErrorInvalidValue` count: 0** (7.14.1: 48 cells). Every cell 7.14.1
fails at launch PASSES on 7.14.0 — TheRock#7992's report confirmed on
gfx1100 via the stable whl-multi-arch index.

Headline shape numbers (kv=32, mask=none): flash S=4096 **8.5-11.2 ms**
(math: 84-91 ms, ~8x); S=16384 flash **116-163 ms**, mem_efficient
**114-203 ms** — where math cannot even allocate (32 GB dense).

## 2. End-to-end benefit (diffusers, p1-zh-scene, bf16, cpu_offload)

First-ever no-workaround generation on this machine: default SDPA
(flash) completes at 1024².

| config | steady s/step @1024² | VRAM peak |
|---|---|---|
| 7140 flash (steps 2-4, two runs) | **1.07 / 1.06** | 16.86 GB |
| 7141 math — Phase 1 protocol baseline (n=many, healthy host) | 3.66 | 18.8 GB |
| 7140 math, this session (4-step runs, thrash regime) | 24-25 | 18.8 GB |
| 7140 math @512² (same session, control) | 0.38 | 16.9 GB |

- **vs like-for-like healthy-host math: 3.4x per-step (3.66 → 1.07), and
  1.9 GB lower VRAM.**
- The 24-25 s/step math runs are NOT a kernel regression: the isolated
  math kernel is identical on both builds (~85 ms @S=4096), and math
  @512² is fast (0.38 s/step). The dense multi-GB score alloc/free per
  step interacts with a memory-pressed host (31 GB weights vs 31.8 GB
  RAM, pagefile regime — finding #4 family) while flash's fixed small
  workspace is immune (1.07 s/step in the same regime). Bonus data point
  for finding #4: the thrash cost is backend-dependent.
- Raw JSONs: `bench/results/raw/2026-11-01-phase4-7140-{flash,math,math-warm,flash-warm,math-512}/`,
  2048² attempt log in the SDD workspace / w2-gen-flash2048.log.

## 3. 2048² bf16 probe: attention UNBLOCKED, VAE decode is the new blocker

Default (flash) at 2048²: the DiT attention path no longer attempts the
32.1 GB dense allocation — flash/mem-efficient handle S≈16k — but the
run OOMs later in the **VAE decoder conv** (`F.conv2d`, tried to allocate
**20.25 GiB**, 15.2 GB already allocated + 6.4 GB reserved-unallocated).

Conclusion: on 7140, 2048² bf16 diffusers is still blocked on 24 GB, but
the blocker moved from attention (kernel bug) to VAE decode memory —
solvable in principle by tiled/split VAE (the ComfyUI route) without any
kernel fix. No attempt made to enable VAE tiling here (out of W2 scope).

## 4. Snapshots

- `bench/results/env/snapshot-20261101-130150.json` (7.14.1): probe
  flash FAIL / mem_eff FAIL / math PASS / cudnn FAIL
- `bench/results/env/snapshot-20261101-133200.json` (7.14.0): probe
  flash PASS / mem_eff PASS / math PASS / cudnn FAIL

The new snapshot fields (transformers/diffusers versions + per-backend
SDPA probe) discriminate the broken/good builds in ~15 s.
