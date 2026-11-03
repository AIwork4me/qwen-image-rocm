# Linux W7900 Optimization Lab — Qwen-Image-2.1 on a single Radeon PRO W7900

**One GPU. One model. One baseline. Three optimization strategies. Measurable results.**

This directory adds a Linux ROCm workstream to qwen-image-rocm: a reproducible
inference-optimization laboratory for Qwen-Image-2.1 on a single
**Radeon PRO W7900 (gfx1100, 48 GB)**, following the methodology

**Baseline → Profiling → Less Computation → Faster Computation →
Parallel & Heterogeneous Computing → Combined Optimization → Quality Gate.**

Every number in these docs resolves to a committed run record under
`bench/results/linux-w7900/`. 中文说明见文末。

## Headline results (measured 2026-11-03, this GPU, 1024², warm = median of 9)

| Config | Warm | vs baseline | Peak VRAM |
|---|---|---|---|
| B0 baseline (bf16, 40 steps) | 55.21 s | 1.00× | 37.7 GB |
| + Turbo 8 steps (L1) | 12.13 s | 4.55× | 37.7 GB |
| + INT8 DiT (F2) | 51.09 s | 1.08× | **31.0 GB** |
| + ck attention (F1) | 45.09 s | 1.22× | 37.7 GB |
| **BEST: Turbo INT8 + default attention** | **9.02 s** | **6.12×** | **31.0 GB** |

Quality: INT8 is near-lossless (LPIPS fidelity 0.005–0.031); Turbo changes the
schedule (distance 0.18–0.34) and **awaits the human three-tier verdict** —
see [P6](P6_COMBINED_OPTIMIZATION.md). Full matrix: [P6](P6_COMBINED_OPTIMIZATION.md).

## Quickstart (Linux, W7900)

Prerequisites: ROCm 7.x with a working `torch` (`torch.cuda.is_available()`
True, gfx1100), ~62 GB disk for weights, Python 3.12.

```bash
git clone <this repo> && cd qwen-image-rocm
python3 -m venv .venv-linux-lab                      # separate lab environment
# install ComfyUI requirements into it (see P0 §6 for the exact recipe)
python -m bench.linux_w7900 doctor                   # MUST pass before measuring
python -m bench.linux_w7900 baseline                 # frozen B0 baseline
python -m bench.linux_w7900 profile                  # pipeline + rocprofv3 kernels
python -m bench.linux_w7900 run --experiment L1      # or F1 F2 LF1 LF2 LF3 L1O BEST H1 H2
python -m bench.linux_w7900 report                   # SUMMARY.json + SUMMARY.md
```

Weights are pinned by SHA256 in `bench/quickstart_config.py` (upstream
revision `aacf31a6`); verify with `python -m bench.quickstart_config
verify-weight --rel <path>`. ComfyUI is pinned at commit `b5a4321` (v0.43.0).

## Documentation index

| Doc | Content |
|---|---|
| [P0_PREFLIGHT.md](P0_PREFLIGHT.md) | hardware/software audit, environment, blockers |
| [P1_BASELINE.md](P1_BASELINE.md) | frozen baseline + reproducibility (2 sessions) |
| [P2_PROFILING.md](P2_PROFILING.md) | pipeline + kernel profiling, bottleneck table, Amdahl |
| [P3_LESS_COMPUTATION.md](P3_LESS_COMPUTATION.md) | Turbo 8-step (historical + official schedules) |
| [P4_FASTER_COMPUTATION.md](P4_FASTER_COMPUTATION.md) | attention backend, INT8, combinations |
| [P5_HETEROGENEOUS_PIPELINE.md](P5_HETEROGENEOUS_PIPELINE.md) | CPU TE, request pipelining (negative results) |
| [P6_COMBINED_OPTIMIZATION.md](P6_COMBINED_OPTIMIZATION.md) | full matrix, BEST, quality gate |
| [REPRODUCTION_GUIDE.md](REPRODUCTION_GUIDE.md) | step-by-step reproduction |
| [LECTURE_DEMO.md](LECTURE_DEMO.md) | classroom demo package (2026-11-19) |
| [CLAIM_EVIDENCE_MATRIX.md](CLAIM_EVIDENCE_MATRIX.md) | every claim → its evidence file |
| [FINAL_ENGINEERING_REPORT.md](FINAL_ENGINEERING_REPORT.md) | executive summary + verdicts |
| [OPEN_ISSUES.md](OPEN_ISSUES.md) | student challenge tasks |

## How quality is judged

Identical to the project's [QUALITY_METHODOLOGY.md](../benchmarks/QUALITY_METHODOLOGY.md):
LPIPS with **declared semantics** (fidelity vs distance), 256 px paired grids,
native-resolution typography crops, determinism noise floor, and the binding
human three-tier verdict (无感 / 略降 / 不可接受). LPIPS is never read as an
absolute quality score; no PASS is inferred from speed alone.

## What this lab is NOT

- Not a multi-GPU claim: one W7900, always.
- Not a Windows comparison: the historical RX 7900 XTX numbers are context,
  never substitutes (different GPU, different attention path, different stack).
- Not a quality approval: the human verdict on the turbo grids is pending.

## 中文说明

本目录为 qwen-image-rocm 增加 Linux ROCm 工作流：在单张 Radeon PRO W7900
（gfx1100，48 GB）上建立可复现的 Qwen-Image-2.1 推理优化实验台。方法学：
基线 → 剖析 → 更少计算（Turbo 8 步）→ 更快计算（注意力后端 / INT8）→
并行与异构（CPU-GPU 流水线，实测为负结果）→ 组合优化 → 质量门禁。
所有数字均可追溯到 `bench/results/linux-w7900/` 下的运行记录；最优配置
（Turbo INT8，9.02 秒，6.12×）的质量终审（无感/略降/不可接受）待-owner
人工网格评审，未通过的优化不进入默认推荐。
