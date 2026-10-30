# qwen-image-rocm

在 **AMD Radeon RX 7900 XTX** + **Windows 原生 ROCm** 上运行 Qwen-Image-2.1
图像生成——可复现的基线（diffusers + ComfyUI）、优化实验，以及面向
ROCm Windows 生态的公开证据。

## 使命

1. 把 ComfyUI + Qwen-Image-2.1 在 7900 XTX 上的出图速度推到极限，
   画质不降或只略降。
2. 用这个真实工作负载发现 ROCm Windows 生态的问题：每个问题都做
   根因分析、最小复现、修复，并向上游提 PR（见 `docs/issues/`）。

**状态：Phase 1 进行中**（diffusers 基线）。完整计划见
[设计文档](docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md)。

## 环境搭建

> TODO：Phase 1 完成时补全——将说明 `reproduce.ps1` 用法、固定的 ROCm
> torch 版本栈、ModelScope 权重下载方式。

## 基准协议

冻结于 [`bench/prompts.json`](bench/prompts.json)：3 条 prompt
（中文场景 / 英文场景 / 文字渲染海报）× 2 个分辨率（1024²、2048²）×
40 步 × seeds `[42, 1337, 20261030]`。结果为 JSON
（schema：`bench/schema/result.schema.json`）+ Markdown 报告
（含中位数、离散度、局限性声明）。

## 许可

- 代码：MIT（见 [LICENSE](LICENSE)）
- 基准数据与报告（`bench/results/`）：CC-BY-4.0
  （见 [docs/DATA_LICENSE.md](docs/DATA_LICENSE.md)）

## English

See [README.md](README.md).
