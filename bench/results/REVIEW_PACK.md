# Phase 3 用户目检包（三档终审：无感 / 略降 / 不可接受）

> 人工终审已完成（A1–A4 无感，A3/A4 更优；A5 略降）。AI 复审（第二道裁决）提示词见 [AI_JUDGE_PROMPT.md](AI_JUDGE_PROMPT.md)。

网格每行一个 prompt（p1 中文场景 / p2 英文场景 / p3 海报长文字），
每 seed 左=bf16-40 对照、右=实验。**海报行请额外看原生分辨率裁剪图**（256px 瓦片看不出文字质量）。
distance 语义 = 图必然不同（不同模型/数值路径），判质量级；fidelity 语义 = 应几乎相同，LPIPS 已给出客观值（噪声底 0.0000）。

---

## A. 需要终审的 5 项（决定最终推荐配置）

### A1. Turbo 8步 + int8 DiT + ck 注意力 — 推荐候选（9.1s，5.2-5.5×）distance

![A1. Turbo 8步 + int8 DiT + ck 注意力 — 推荐候选（9.1s，5.2-5.5×）distance](2026-11-01-e8-turbo-int8-ck/quality_grid.png)

### A1. Turbo 8步 + int8 DiT + ck 注意力 — 推荐候选（9.1s，5.2-5.5×）distance — 海报原生裁剪

![A1. Turbo 8步 + int8 DiT + ck 注意力 — 推荐候选（9.1s，5.2-5.5×）distance — 海报原生裁剪](2026-11-01-e8-turbo-int8-ck/quality_crops_poster.png)

### A2. Turbo 8步 + int8 DiT（9.1-9.2s，5.3×）distance

![A2. Turbo 8步 + int8 DiT（9.1-9.2s，5.3×）distance](2026-11-01-e2-turbo-int8/quality_grid.png)

### A2. Turbo 8步 + int8 DiT（9.1-9.2s，5.3×）distance — 海报原生裁剪

![A2. Turbo 8步 + int8 DiT（9.1-9.2s，5.3×）distance — 海报原生裁剪](2026-11-01-e2-turbo-int8/quality_crops_poster.png)

### A3. Turbo 8步 bf16（11.1-13.1s，3.7-4.5×）distance

![A3. Turbo 8步 bf16（11.1-13.1s，3.7-4.5×）distance](2026-11-01-e1-turbo/quality_grid.png)

### A3. Turbo 8步 bf16（11.1-13.1s，3.7-4.5×）distance — 海报原生裁剪

![A3. Turbo 8步 bf16（11.1-13.1s，3.7-4.5×）distance — 海报原生裁剪](2026-11-01-e1-turbo/quality_crops_poster.png)

### A4. ck 注意力 · 40步 bf16（35-37s，1.3-1.37×）— 数值路径不同，判质量级

![A4. ck 注意力 · 40步 bf16（35-37s，1.3-1.37×）— 数值路径不同，判质量级](2026-11-01-e4-ck/quality_grid.png)

### A4. ck 注意力 · 40步 bf16（35-37s，1.3-1.37×）— 数值路径不同，判质量级 — 海报原生裁剪

![A4. ck 注意力 · 40步 bf16（35-37s，1.3-1.37×）— 数值路径不同，判质量级 — 海报原生裁剪](2026-11-01-e4-ck/quality_crops_poster.png)

### A5. w4a8 TE · 40步（预期难过关：LPIPS max 0.41）fidelity

![A5. w4a8 TE · 40步（预期难过关：LPIPS max 0.41）fidelity](2026-11-01-e2-w4a8-te/quality_grid.png)

### A5. w4a8 TE · 40步（预期难过关：LPIPS max 0.41）fidelity — 海报原生裁剪

![A5. w4a8 TE · 40步（预期难过关：LPIPS max 0.41）fidelity — 海报原生裁剪](2026-11-01-e2-w4a8-te/quality_crops_poster.png)


---

## B. 近无损项（LPIPS 0.004–0.031，可快速扫一眼）

- [int8 DiT（0.010/0.012/0.005）](2026-11-01-e2-int8-dit/quality_grid.png)
- [int8 TE（0.023/0.016/0.004）](2026-11-01-e2-int8-te/quality_grid.png)
- [int8 DiT+TE（0.029/0.008/0.006）](2026-11-01-e2-int8-dit-te/quality_grid.png)
- [VAE tiled（0.004；速度已被否决，仅供画质参考）](2026-11-01-e6-vaetiled-v2/quality_grid.png)
- [split 注意力（0.007）](2026-11-01-e4-split/quality_grid.png)

---

## C. 逐字节一致项（LPIPS 0.0000，无需目检）

attn: quad / 默认无包装 / --disable-smart-memory / --highvram / --cache-none / --fast fp16_accumulation
（纯性能杠杆，输出与对照 bit 级相同；后三者因速度已被否决）

---

## D. 2048² 样张（解锁验证，昨日起从不可能变为可用）

![2048 40步 int8](2026-11-01-e2-int8-dit-te-2048-probe/sample-2048-40step.png)
↑ 40 步 int8 DiT+TE @ 2048²（328s）

![2048 8步 turbo-int8](2026-11-01-e2-turbo-int8-2048-probe/sample-2048-8step.png)
↑ Turbo 8 步 int8 @ 2048²（42.2s）

完整原始大图在本地 `results/raw/*2048-probe/`（未入库，体积纪律）。
