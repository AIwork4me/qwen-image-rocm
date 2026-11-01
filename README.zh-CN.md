# qwen-image-rocm

在 **AMD Radeon RX 7900 XTX** + **Windows 原生 ROCm** 上运行 Qwen-Image-2.1
图像生成——可复现的基线（diffusers + ComfyUI）、优化实验，以及面向
ROCm Windows 生态的公开证据。

## 使命

1. 把 ComfyUI + Qwen-Image-2.1 在 7900 XTX 上的出图速度推到极限，
   画质不降或只略降。
2. 用这个真实工作负载发现 ROCm Windows 生态的问题：每个问题都做
   根因分析、最小复现、修复，并向上游提 PR（见 `docs/issues/`）。

**状态：Phase 3 完成**（优化循环：1024² 提速 5.2–5.5×，2048² 解锁；
下一步 Phase 4 RCA）。见
[设计文档](docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md)与
[Phase 3 计划](docs/superpowers/plans/2026-10-31-phase3-optimization-loop.md)。

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

## Phase 2 结果（ComfyUI 基线，1024²，bf16，40 步）

ComfyUI 0.43.0（固定 commit）、独立 uv venv、同一指定 ROCm 栈、
euler/simple/cfg-1（官方 Qwen-Image-2.1 模板默认）、API 顺序驱动、
默认注意力（开箱即用——见发现 5）。报告：
[comfyui](bench/results/2026-10-31-comfyui-1024/report.md) ·
跨框架对比图：
[cross_framework.png](bench/results/2026-10-31-comfyui-1024/cross_framework.png)

| 框架（1024²，warm） | 总耗时中位 (s) | s/step | 显存 |
|---|---|---|---|
| diffusers + cpu_offload (math) | 239 – 254 | 稳态 3.60 – 3.70 | 18.8 GB |
| **ComfyUI（默认注意力）** | **45 – 51** | ~1.1（按执行时间估算） | 16.6 GB |

同等数值配置下 ComfyUI warm 端到端快约 5 倍：diffusers 每轮付 ~90s 的
cpu_offload 权重搬运（31GB 过 PCIe）+ 3.66s/step 去噪；ComfyUI 让 DiT
常驻显存、每换 prompt 一次性换模型（~350s warmup，其后缓存）。该框架
差异数据即 Phase 3 的基线。注：ComfyUI API 不暴露逐步耗时，总耗时取
服务器执行时间。

**更正（Phase 3，2026-11-01）**：45–51s 稳态数字**不含文本编码**——正式
测量与 warmup 只差 seed，ComfyUI 节点缓存直接跳过 `CLIPTextEncode`
（v1.3 websocket 计时揭示；真实 TE 计算 bf16 3–7s / int8 1.1–2.6s）。

## Phase 3 结果（优化循环，2026-11-01，协议 v1.3）

同会话、同重启机制；所有提速均为对**同会话 bf16 影子对照**
（48.2 / 50.2 / 48.4s）的配对比值。节点级计时（文本编码/去噪/VAE）与
真实显存峰值来自新增 websocket 监视器。总表：
[summary](bench/results/2026-11-01-phase3-summary/report.md) · 各实验
`quality.md` + 对比网格 · [目检包](bench/results/REVIEW_PACK.md)。

| 手段（1024²，warm） | 总耗时 (s) | 提速 | 画质（对 bf16-40 的 LPIPS） |
|---|---|---|---|
| bf16 影子对照 | 48.2–50.2 | 1.00× | —（噪声底 0.0000） |
| **Turbo 8 步 + int8 DiT + ck 注意力** | **9.1（全 prompt 一致）** | **5.2–5.5×** | distance 0.21–0.36（待目检） |
| Turbo 8 步 + int8 DiT | 9.1–9.2 | 5.3× | distance 0.19–0.35 |
| Turbo 8 步（bf16） | 11.1–13.1 | 3.7–4.5× | distance 0.19–0.28 |
| 仅 ck 注意力（40 步 bf16） | 35.2–37.5 | 1.30–1.37× | 数值路径不同（网格判定） |
| int8 DiT / TE（40 步） | 44.5–50.5 | ~1.0× | 保真 0.004–0.031（近无损） |
| --disable-smart-memory | 42.4–46.4 | 1.06–1.14× | 逐字节一致 |
| --highvram / --fast fp16_accumulation | p3 163 / 224 | 0.22–0.30×（p3） | 一致但严重变慢 |
| torch.compile（diffusers 侧） | 阻断 | — | `TritonMissing`（inductor 建后端即失败） |

要点：

1. **2048² 解锁**（原"所有后端均不可能"，发现 2）：原生 int8 权重
   （DiT 7.26GB + TE 9.35GB）+ sub-quadratic 注意力跑通 2048×2048——
   40 步 328s，**Turbo-int8 仅 42.2s**。
2. **原生 int8 量化近无损且零成本**：普通 `UNETLoader` 自动识别
   `.comfy_quant`；1024² 速度持平、权重减半。此模型**无 fp8**；w4a8 TE
   条件漂移大（LPIPS 最高 0.41），int8 是甜点。
3. **ck 注意力（`--use-ck-attention`）是 gfx1100 上唯一更快的后端**
   （1.30–1.37×）；split 略慢、quad=默认、`--use-pytorch-cross-attention`
   即使 math-hard 包装也被发现 1 阻断（TE 路径仍触发坏 kernel）。
4. **文本编码便宜、模型换入换出贵**：新 prompt 只付 1.1–2.6s TE 计算
   （int8），但内存压力下模型对换要 ~60–470s——24GB 卡跑 31.8GB 权重的
   真实"新 prompt"成本。
5. **节点缓存价值 ~30%**：`--cache-none` 只有 0.68–0.71×。

## ROCm Windows 生态发现（Phase 1-4）

1. **flash 与 mem-efficient SDPA 启动失败** —— **上游已根因定位**
   （TheRock#7315/#7992：torch 2.12.0+rocm7.14.1 Windows 轮子的
   AOTriton 运行时/镜像版本错配），**本地已验证**（无权重 192 格复现：
   S=64 起即失败；同索引 `2.12.0+rocm7.14.0` = 零启动失败），
   **修复收益已测量**（7.14.0 flash：1024² 1.07 s/step，比 math 快
   3.4×，省 1.9GB 显存）——
   [issue](docs/issues/2026-10-30-hiperrorinvalidvalue-qwen3vl-textencoder.md)、
   [W2 证据](docs/issues/evidence/phase4-w2-7140-verification.md)
2. **2048²（原生分辨率）**：在好的 7.14.0 构建上注意力已不再是阻碍
   （flash 可跑 S≈16k），但 bf16 VAE 解码 OOM（单次 20.25GB conv
   分配）——实测 2048² 路线仍是 ComfyUI + 原生 int8（Phase 3：
   40 步 328s / turbo 42s）。
3. **AMD 轮子源无 Windows Triton**（2026-11-01 复核：TheRock PR#4006
   已合并但未发布轮子；nightly 的 triton 仅 Linux）→
   FlexAttention/torch.compile 走慢速回退——
   [issue](docs/issues/2026-10-30-no-triton-windows-rocm.md)
4. **cpu_offload 首轮 warmup 页文件抖动**（6× 步长减速，可自恢复）
   （32GB 内存主机）；Phase 4 补充：抖动代价与后端相关（flash 免疫，
   稠密 math 分配受害最深）——
   [issue](docs/issues/2026-10-30-warmup-pagefile-thrash-cpu-offload.md)
5. **ComfyUI 通过启动探测在 SDPA 后端 bug 下幸存**：它同样撞上 flash
   注意力的 `invalid argument` 失败，但自动禁用并回退到次二次核——
   而 diffusers/transformers 会整体失败。同样的坏 kernel，不同的消费者
   韧性；证据（日志行 + 两张输出图的 SHA256）见
   [issue 1](docs/issues/2026-10-30-hiperrorinvalidvalue-qwen3vl-textencoder.md)。
   Phase 4 已把该探测模式提议发到上游——
   [transformers#50211](https://github.com/huggingface/transformers/issues/50211)
   （6 项已批准贡献已于 2026-11-01 全部发布：[INDEX](docs/upstream/INDEX.md)）。

## 许可

- 代码：MIT（见 [LICENSE](LICENSE)）
- 基准数据与报告（`bench/results/`）：CC-BY-4.0
  （见 [docs/DATA_LICENSE.md](docs/DATA_LICENSE.md)）

## English

See [README.md](README.md).
