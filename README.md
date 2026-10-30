# qwen-image-rocm

Qwen-Image-2.1 image generation on **AMD Radeon RX 7900 XTX** under
**Windows-native ROCm** — reproducible baselines (diffusers + ComfyUI),
optimization experiments, and public evidence for the ROCm-on-Windows
ecosystem.

## Mission

1. Push image-generation throughput of ComfyUI + Qwen-Image-2.1 on the
   7900 XTX to its limit, with no or only slight quality loss.
2. Use this real workload to surface ROCm-on-Windows problems: every issue
   gets root-cause analysis, a minimal reproducer, a fix, and an upstream
   PR (see `docs/issues/`).

**Status: Phase 1 in progress** (diffusers baseline). See the
[design document](docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md)
for the full plan.

## Setup

> TODO: completed in Phase 1 — will describe `reproduce.ps1`, the pinned
> ROCm torch stack, and ModelScope weight download.

## Benchmark protocol

Frozen in [`bench/prompts.json`](bench/prompts.json): 3 prompts
(Chinese scene / English scene / text-rendering poster) × 2 resolutions
(1024², 2048²) × 40 steps × seeds `[42, 1337, 20261030]`. Results are
JSON (schema: `bench/schema/result.schema.json`) + a Markdown report with
medians, spread, and limitations.

## License

- Code: MIT (see [LICENSE](LICENSE))
- Benchmark data & reports (`bench/results/`): CC-BY-4.0
  (see [docs/DATA_LICENSE.md](docs/DATA_LICENSE.md))

## 中文说明

见 [README.zh-CN.md](README.zh-CN.md)。
