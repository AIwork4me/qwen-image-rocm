# Qwen-Image 2.1 · AMD Radeon GPU 原生 Windows ROCm

**原生 Windows ROCm · 可复现图像生成 · AMD Radeon RX 7900 XTX 24 GB**

在 24 GB Radeon 显卡上、原生 Windows ROCm 环境下本地运行 Qwen-Image-2.1 —— 一条命令的快速上手、冻结协议的基准测试、经过质量门禁的优化组合，以及页面上每一个数字背后的公开证据。

| 本栈实测 | 数值 | 含义（与边界） |
|---|---|---|
| **1024² 生成 · Fast 模式** | **~8–9 秒/张（热态）** | 同一 prompt、模型常驻、文本编码缓存命中。完整冷启动 20–46 s，改 prompt ≈ +1.2 s → [真实延迟](docs/benchmarks/REAL_WORLD_LATENCY.md) |
| **相对 bf16-40 基线加速** | **5.2–5.5×（热态、同会话配对）** | 同会话实测配对；8 步 turbo 输出必然不同——画质经人工目检裁决，未宣称无损 |
| **2048² 原生分辨率** | **~40–42 秒/张** | 已演示并跨会话/跨 prompt 复测；有界验证仍待补 → [明细](docs/benchmarks/2048_VALIDATION.md) |
| 测试硬件 / 系统 | RX 7900 XTX (gfx1100) · Windows 11 | 原生 Windows ROCm，不用 WSL2、不静默回退 CPU。其他 GPU 未测（默认拒绝执行） |
| ROCm 栈 | torch 2.12.0+rocm7.14.1 · ComfyUI 固定 commit | AMD 轮子固定版本、ComfyUI 锁 commit、运行记录过 schema 校验 |

*以上每条声明都能对应到已提交的运行记录：[声明-证据矩阵](docs/benchmarks/CLAIM_EVIDENCE_MATRIX.md)。*

## 真实输出（未修图，可溯源）

| 1024² Fast · 中文场景 | 1024² Fast · 英文场景 | 1024² Fast · 中文排版海报 |
|---|---|---|
| ![江南水乡夕照](docs/gallery/fast-1024-p1-zh-scene-seed42.png) | ![山脊徒步者与云海](docs/gallery/fast-1024-p2-en-scene-seed42.png) | ![深空飞船电影海报、中文标题锐利](docs/gallery/fast-1024-p3-poster-seed42.png) |

| 2048² 原生 · Fast | bf16-40 基线（Phase 2） | turbo-int8 vs bf16 配对网格 |
|---|---|---|
| ![2048 原生山景](docs/gallery/fast-2048-p2-en-scene-seed42.png) | ![Phase-2 基线样张](bench/results/2026-10-31-comfyui-1024/sample-p1-zh-r0.png) | ![左 bf16-40，右 turbo-int8-ck，3 prompt × 3 seed](bench/results/2026-11-01-e8-turbo-int8-ck/quality_grid.png) |

全部图片可追溯到运行记录（实验、prompt、seed、步数）：
[docs/gallery/PROVENANCE.md](docs/gallery/PROVENANCE.md)。不使用其他模型生成图、不做修饰。

## 快速开始

前置：Windows 11、Radeon RX 7900 XTX、较新 Adrenalin 驱动、
[uv](https://docs.astral.sh/uv/)、git、Fast 模式权重约 18 GB 磁盘。

```powershell
git clone https://github.com/AIwork4me/qwen-image-rocm.git
cd qwen-image-rocm
.\quickstart.ps1 -Mode Fast        # 数分钟内出第一张图；热态 ~8-9 s/张
.\quickstart.ps1 -Mode Quality     # bf16 40 步，与基线逐位一致
.\quickstart.ps1 -Mode Fast -Resolution 2048
```

一条命令完成：Windows/GPU/gfx1100 检查 → 隔离 venv + 固定版本 AMD ROCm 轮子
→ 固定 commit 的 ComfyUI（不匹配即拒绝执行）→ 权重完整性（固定上游
revision `aacf31a6` 的 SHA256，摘要内置于仓库，**每个文件**都强校验、断点
续传）→ **要求 Radeon 设备**的服务健康门
（不允许静默 CPU 回退）→ 用与基准测试相同的驱动执行生成 → 按统一口径打印
`服务器启动 / 就绪到首图 / 完整冷启动 / 热态均值+中位数`。首次运行需下载权重；
此后完整冷启动约 20 秒（缓存热）至 46 秒（全新安装）。

Phase-1 diffusers 复现入口保留：`.\reproduce.ps1 -Quick`。

## Fast 与 Quality

| | Fast | Quality |
|---|---|---|
| 配置 | Turbo 8 步 · int8 DiT + int8 TE · `--use-ck-attention` · `--disable-smart-memory` | bf16 40 步 · `--disable-smart-memory` |
| 1024² 热态 | ~8–9 s | ~45–51 s |
| 2048² | ✅ ~40–42 s | ❌（bf16 VAE 解码在 24 GB 上 OOM） |
| 输出 vs 基线 | 不同（8 步调度）。裁决状态：turbo-int8+ck 已在冻结网格上判"无感"（A1）；**完整三联组合仅通过 vs e8 的 LPIPS 门（0.058/0.012/0.014，p1/p2/p3），正式网格裁决待 owner 复核（[#5](https://github.com/AIwork4me/qwen-image-rocm/issues/5)）**；int8 量化近无损（LPIPS 0.004–0.060） | **逐位一致**（LPIPS 0.0000） |
| 磁盘权重 | ~18 GB | ~32 GB |

两个档位都是冻结的实验清单（[bench/quickstart_config.py](bench/quickstart_config.py)），
quickstart 不可能偏离已测配置。画质评判方法见
[QUALITY_METHODOLOGY.md](docs/benchmarks/QUALITY_METHODOLOGY.md)。

## 硬件支持矩阵

| GPU / 系统 | 状态 |
|---|---|
| RX 7900 XTX (gfx1100) · Windows 11 原生 | ✅ **已测试——本页全部数字** |
| 其他 gfx1100 Radeon（7900 XT/GRE、7800 XT…）· Windows 11 | ⚠️ 预期可用；未实测——quickstart 需 `-AllowUntestedGpu` |
| gfx1151 / RDNA4、核显 Radeon | ⚠️ 未测试 |
| Linux ROCm | 不在本仓库范围（Windows-ROCm 结论未必适用） |
| NVIDIA / Intel / CPU | ❌ 不支持；quickstart 直接拒绝 |

## 真实延迟（Fast，1024²）

统一口径——精确定义见 [REAL_WORLD_LATENCY.md](docs/benchmarks/REAL_WORLD_LATENCY.md)：

| 指标 | 缓存热的主机 | 全新安装 |
|---|---|---|
| 服务器启动 | 8.1 s | 28.3 s |
| 就绪到首图 | 12.1 s | 17.2 s |
| **完整冷启动**（启动 → 首图） | **20.2 s** | **45.5 s** |
| 换 prompt（文本变化） | ~10 s | — |
| 热态重复（换 seed）均值 | 8.1–8.6 s | — |
| 2048² Fast（就绪到首图 / 热态） | 43.3 s / 40.2 s | 单 prompt 探测 |

Quality（bf16-40）：完整冷启动 67.5 s、热态 ~46 s。重启后的冷启动
**未测**；VRAM 数字为 0.5 s 采样值（下界）。

## 复现基准测试

```powershell
# 协议级（每变体独立服务器、3 prompt × 3 seed、质量门禁）：
powershell -File bench\run_variant.ps1 -Experiment p3-turbo-int8-ck-te-nosmart-1024x1024 -Date mydate
# Phase-1 diffusers 基线：
.\reproduce.ps1 -Full
```

冻结协议：3 个 prompt（中文场景/英文场景/中文排版海报）× seeds
[42, 1337, 20261030]，euler/simple，cfg 1.0，cold+warmup+measured 纪律与
防缓存种子（[bench/prompts.json](bench/prompts.json)、
[schema](bench/schema/result.schema.json)）。历史结果只读；修正以新运行 +
勘误落地，绝不改写原始数据。

关键结果（实测中位数；完整表见
[Phase-3 汇总](bench/results/2026-11-01-phase3-summary/report.md)）：

| 杠杆（1024²，热态） | 总耗时 | vs 同会话 bf16 对照 | 画质 |
|---|---|---|---|
| Turbo-int8 + ck（e8） | 9.1 | 5.2–5.5× | distance 0.21–0.36 → 用户裁决：无感 |
| **完整生产组合（r1）** | **8.0–9.2** | 跨会话 ~5.5–6.0×* | vs e8 LPIPS：0.058/0.012/0.014（fidelity） |
| 仅 ck 注意力（40 步） | 35–37 | 1.30–1.37× | 数值路径不同 → 网格裁决 |
| int8 DiT / TE（40 步） | 45–50 | ~1.0× | 近无损 0.004–0.060 |
| `--disable-smart-memory` | 42–46 | 1.06–1.14× | 逐位一致 |
| `--highvram`、`--fast fp16_accumulation` | 163/224 | 0.2–0.3× | 有数据地否决 |
| diffusers + cpu_offload 基线 | 239–254 | — | Phase 1 |

\* 仅为跨会话参考；同会话配对声明以 e8 行为准。

## 架构与优化

- **ComfyUI 为何比 diffusers 快 5×**：diffusers 每次运行付出 ~90 s 的
  cpu_offload PCIe 搬运（31 GB）+ 3.66 s/步；ComfyUI 保持 DiT 常驻。详见
  [Phase 2 报告](bench/results/2026-10-31-comfyui-1024/report.md)。
- **int8 解锁**：原生 `.comfy_quant` 检查点由普通 loader 自动识别（无自定义
  节点）——权重减半、1024² 速度持平，并且是 2048² 注意力+权重塞进 24 GB 的
  唯一路径。
- **测量设施（协议 v1.3）**：websocket 节点/步级计时（文本编码/去噪/VAE 分
  解）、节点缓存命中核算、采样式 VRAM 峰值、每变体完整服务器生命周期 +
  从服务器日志抓取注意力路径证据（[bench/comfyui_client.py](bench/comfyui_client.py)）。

## 已知限制

- 热态数字 ≠ 用户延迟（冷/换词/热三分，
  见[真实延迟](docs/benchmarks/REAL_WORLD_LATENCY.md)）。
- 2048² 验证深度为两次探测，非长时间稳定性测试
  （[台账](docs/benchmarks/2048_VALIDATION.md)）。
- VRAM 为 0.5 s 采样值——瞬态峰值的下界。
- 画质裁决只覆盖冻结的 3 prompt × 3 seed 集合，不外推。
- torch.compile/FlexAttention 被阻断：Windows ROCm 无 Triton 轮子。

## ROCm-on-Windows 发现与上游贡献

以真实工作负载驱动的 RCA 与最小复现——已于 2026-11-01 全部发上游
（[索引](docs/upstream/INDEX.md)）：

1. torch 2.12.0+rocm7.14.1 Windows 上 flash/高效 SDPA 自 S=64 起
   `hipErrorInvalidValue` —— 根因为轮子内 AOTriton 运行时/镜像不匹配
   （TheRock#7315/#7992）；本地以免权重 192 格复现验证；同索引 7.14.0
   干净且 flash 快 3.4×——切栈是显式的用户决策，仓库默认保持 7.14.1 +
   `QIR_SDP=math` workaround。
   [TheRock#7315 评论](https://github.com/ROCm/TheRock/issues/7315#issuecomment-6554228687) ·
   [transformers#50211](https://github.com/huggingface/transformers/issues/50211)
2. Windows ROCm 无 Triton 轮子（已核实的发行缺口；TheRock PR#4006 已合未发）
   → [issue 文档](docs/issues/2026-10-30-no-triton-windows-rocm.md)
3. 32 GB 内存主机 cpu_offload 首次预热 pagefile 抖动 →
   [accelerate#4488](https://github.com/huggingface/accelerate/issues/4488)
4. 韧性不对称：ComfyUI 靠启动探测躲过坏 SDPA 内核并回退；diffusers/
   transformers 整个调用失败——探测模式提案已发 transformers#50211。
5. hf_transfer/hub 在不稳定镜像上的断点行为 →
   [huggingface_hub#4196 评论](https://github.com/huggingface/huggingface_hub/issues/4196#issuecomment-6554229435)
6. RDNA3-Windows 注意力后端性能数据：`--use-ck-attention` 1.30–1.37× →
   [comfy-kitchen#292](https://github.com/Comfy-Org/comfy-kitchen/issues/292)；
   VAEDecodeTiled 与 fp16_accumulation 回归 →
   [ComfyUI#17469](https://github.com/Comfy-Org/ComfyUI/issues/17469) ·
   [ComfyUI#17470](https://github.com/Comfy-Org/ComfyUI/issues/17470)

## 路线图

- [ ] 2048² 有界矩阵（3 prompt × 3 seed，约 15 分钟 GPU）——补最大证据缺口
- [ ] 生产组合网格的正式三档裁决（owner 复核）
- [ ] 重启后冷启动测量（真实磁盘首启）
- [ ] 切栈试用：上游修复进入稳定 tag 后，默认切 7.14.0 flash（注意力 3.4×）
- [ ] 更广的画质套件（人像、产品、长英文 prompt）——独立、明确标注的新集
- [ ] 可选：7900 XT / GRE 的 gfx1100 家族验证

## 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。CPU 测试门：
`uv run --with pytest --with jsonschema --with matplotlib --with pillow --with numpy --with requests pytest tests/ -v`
（无需 GPU；GPU 硬件验证是独立的 self-hosted workflow）。
Bug 报告需附 `tools/snapshot_env.py` 输出——见 issue 模板。

## 许可证与致谢

- 本项目代码：**MIT**（[LICENSE](LICENSE)）
- 基准数据与报告（`bench/results/`、`docs/benchmarks/`）：**CC-BY-4.0**
  （[docs/DATA_LICENSE.md](docs/DATA_LICENSE.md)）
- 模型权重：Qwen-Image-2.1 与 Qwen3-VL 遵循各自上游许可，由使用者自行
  下载，绝不入库（[docs/weights.md](docs/weights.md)）
- ComfyUI（GPL-3.0）在安装时按固定 commit 克隆；本仓库不复制其代码。
  完整归因与边界：[docs/LEGAL_AND_ATTRIBUTION.md](docs/LEGAL_AND_ATTRIBUTION.md)

*独立社区基准项目——非 AMD 或阿里巴巴/Qwen 官方项目。所有数字均在维护者的
RX 7900 XTX 上实测，附可复现证据。*

## English

English README: [README.md](README.md).
