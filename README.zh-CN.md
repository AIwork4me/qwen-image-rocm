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

前置条件：Windows 11、AMD Radeon RX 7900 XTX（gfx1100）、较新的 Adrenalin
驱动、[uv](https://docs.astral.sh/uv/)、git。

"陌生人标准"一键复现（30 分钟门槛）：

```powershell
.\reproduce.ps1 -Quick    # 单配置：p2-en-scene，1024²，40 步，seed 42
.\reproduce.ps1 -Full     # 完整 Phase 1 协议（约 1.5–3 小时）
```

它会创建隔离的 `.venv-repro`、安装固定的 AMD ROCm 栈、跑 HIP 冒烟、从
ModelScope 下载权重（约 30GB，仅一次），然后执行。

手动等价步骤（`reproduce.ps1` 自动化的内容）：

1. `uv venv phase1-diffusers/.venv --python 3.12 --seed`
2. **只**用指定的 AMD 轮子命令装 torch（逐字执行）：
   ```
   python -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1100]==2.12.0+rocm7.14.1" "torchvision[device-gfx1100]==0.27.0+rocm7.14.1" "torchaudio==2.11.0+rocm7.14.1"
   ```
3. `python -m pip install -r phase1-diffusers/requirements.txt`，随后断言
   `torch.__version__.endswith("rocm7.14.1")`（防止被换成 PyPI 版）
4. `modelscope download --model Qwen/Qwen-Image-2.1 --local_dir weights/diffusers-format`
5. `python -I phase1-diffusers/smoke_hip.py`（必须输出 `gcn_arch=gfx1100`）
6. 设置 `QIR_SDP=math`（本栈必需——见下方发现 1），然后出图：
   `python -I phase1-diffusers/generate.py --prompt-id p2-en-scene
   --width 1024 --height 1024 --steps 40 --seed 42 --out results/raw/repro`

每份结果的环境证据在 `bench/results/env/`（由 `tools/snapshot_env.py`
生成）。精确冻结的依赖清单见 `phase1-diffusers/requirements.lock.txt`
（pip freeze；ROCm 栈不在 PyPI 上，该锁依赖 AMD 轮子源）。

## 基准协议

冻结于 [`bench/prompts.json`](bench/prompts.json)：3 条 prompt
（中文场景 / 英文场景 / 文字渲染海报）× 40 步 ×
seeds `[42, 1337, 20261030]`。**仅在 1024² 执行**——在 24GB RDNA3 卡 +
当前 Windows ROCm 栈的任何可用注意力后端上，2048² 目前无法完成
（见下方发现）。结果为 JSON（schema：`bench/schema/result.schema.json`）
+ Markdown 报告（含中位数、离散度、局限性声明）。

## Phase 1 结果（diffusers 基线，1024²，bf16，40 步）

每配置 3 次测量取中位；完整报告：
[math](bench/results/2026-10-31-math-1024/report.md) ·
[flex](bench/results/2026-10-31-flex-1024/report.md)

| DiT 注意力后端 | s/step（稳态中位） | 总耗时（中位） | 显存 |
|---|---|---|---|
| math SDPA      | 3.60 – 3.70 | 239 – 254 | 18.8 GB |
| flex（无 Triton） | 16.1 – 18.9 | 756 – 875 | 20.8 GB |

s/step = 第 2..40 步的中位数（稳态）；`step_times_s[0]` 含文本编码 +
cpu-offload 权重恢复，被排除（协议 v1.1——见各报告的 Limitations 节）。

环境证据：`bench/results/env/snapshot-20261030-212234.json`。

## ROCm Windows 生态发现（Phase 1）

1. **flash 与 mem-efficient SDPA 后端报 `hipErrorInvalidValue`**
   （Qwen3-VL 与 Qwen-Image-2.1 DiT 形状）——
   [issue](docs/issues/2026-10-30-hiperrorinvalidvalue-qwen3vl-textencoder.md)
2. **2048²（原生分辨率）不可达**：所有内存高效后端损坏或缺失；
   math 与 flex 无 Triton 回退都需要单次 32.1GB 稠密注意力分配。
3. **AMD 轮子源无 Windows Triton** → FlexAttention/torch.compile 走慢速
   回退——[issue](docs/issues/2026-10-30-no-triton-windows-rocm.md)
4. **cpu_offload 首轮 warmup 页文件抖动**（6× 步长减速，可自恢复）
   （32GB 内存主机）——
   [issue](docs/issues/2026-10-30-warmup-pagefile-thrash-cpu-offload.md)

## 许可

- 代码：MIT（见 [LICENSE](LICENSE)）
- 基准数据与报告（`bench/results/`）：CC-BY-4.0
  （见 [docs/DATA_LICENSE.md](docs/DATA_LICENSE.md)）

## English

See [README.md](README.md).
