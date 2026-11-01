# Launch kit (v0.1.0) — drafts only, nothing auto-posted

Everything here uses **measured, qualifier-carrying numbers** from
[docs/benchmarks/CLAIM_EVIDENCE_MATRIX.md](../benchmarks/CLAIM_EVIDENCE_MATRIX.md).
Do not strip the qualifiers when posting. Do not claim AMD/Alibaba
affiliation. Do not fabricate community reactions.

## 1. GitHub release announcement (EN)

> **qwen-image-rocm v0.1.0 — Qwen-Image 2.1 on Radeon, native Windows ROCm**
>
> One command to your first image on an RX 7900 XTX:
> `.\quickstart.ps1 -Mode Fast` → ~8–9 s/image warm at 1024² (5.2–5.5× vs
> the measured bf16-40 baseline, same-session paired), ~40–42 s at native
> 2048² (probe-tier evidence), cold start 12–17 s, changed prompt ~10 s.
> Bit-identical Quality mode, reproducible benchmark protocol, schema-
> validated evidence for every number, and 7 upstream ROCm/ComfyUI
> contributions along the way. Not affiliated with AMD or Alibaba. Windows 11
> + 7900 XTX tested; other cards fail closed pending your reports.

## 2. LinkedIn (EN, ~120 words)

> I've been benchmarking Qwen-Image 2.1 on an AMD Radeon RX 7900 XTX under
> native Windows ROCm. Open-source, one-command quickstart, every number
> traceable to a committed run record: ~8–9 s/image warm at 1024² (5.2–5.5×
> vs bf16-40, paired same-session), native 2048² in ~40–42 s, cold/fresh/
> warm latency reported separately because warm-only numbers mislead. The
> process surfaced real ROCm-on-Windows bugs — one wheel-level AOTriton
> mismatch root-caused with a weights-free repro and posted upstream, plus
> six more contributions. If you run Radeon + Windows, try it and file a GPU
> report: the tested matrix starts with the 7900 XTX and grows from your
> data. #ROCm #AMD #AIGC #opensource

## 3. X/短文 (EN + zh)

> EN: Qwen-Image 2.1 on Radeon 7900 XTX, native Windows ROCm, one command:
> 8–9 s/image @1024 (warm, paired 5.2–5.5×), 2048² native ~41 s, every
> number has a committed run record. OSS, no affiliation.
> github.com/AIwork4me/qwen-image-rocm
>
> zh：7900 XTX 原生 Windows ROCm 跑 Qwen-Image-2.1：一条命令，1024² 热态
> 8–9 秒/张（配对实测 5.2–5.5×），原生 2048² 约 41 秒；冷/换词/热分开报告，
> 每个数字可溯源。开源，与 AMD/阿里无关。

## 4. Reddit (r/AMDHelp / r/LocalLLaMA / r/StableDiffusion 技术向)

Title: `Qwen-Image 2.1 on RX 7900 XTX under native Windows ROCm: measured
8–9 s/image @1024² warm, 2048² native unlocked (one-command repro, evidence
for every number)`

Body skeleton: (1) what/why — no public Windows-RDNA3 numbers existed;
(2) table: cold 12–17 s / fresh ~10 s / warm 8–9 s / 2048² 40–42 s with
"what these regimes mean"; (3) the ROCm findings (wheel-level AOTriton
mismatch, no Triton wheels, pagefile thrash) each with its upstream link;
(4) honest limits: single GPU tested, 2048 = probe-tier, quality verdicts
are human-judged on a frozen set; (5) ask: GPU reports from other Radeon
cards. No hype words. Answer comments with records, not vibes.

## 5. 中文社区（知乎/掘金/V2U/即刻）

标题方向：`在 7900 XTX 上用原生 Windows ROCm 跑 Qwen-Image-2.1：实测
8–9 秒/张（1024²），原生 2048² 解锁——附完整复现与证据链`
要点：一条命令 quickstart；冷/换词/热三种延迟分开给；int8 近无损的
LPIPS 证据；三个 ROCm-on-Windows 发现与上游链接（TheRock/transformers/
accelerate/ComfyUI）；明确"只在 7900 XTX 实测、其他卡欢迎提 GPU 报告"。

## 6. Maintainer outreach (DM/email, short)

> Hi — I run an independent benchmark putting Qwen-Image 2.1 on Radeon
> (native Windows ROCm, 7900 XTX). It produced data your trackers may want:
> a Windows-wheel AOTriton mismatch repro (TheRock#7315 comment), RDNA3-
> Windows attention-backend numbers (comfy-kitchen#292), and a resilience
> pattern ComfyUI uses that diffusers/transformers don't (transformers#50211).
> Repo with one-command repro: https://github.com/AIwork4me/qwen-image-rocm
> Happy to run follow-ups on the 7900 XTX if useful.

## Assets

- Social preview: `assets/social-preview.png` (1280×640, real outputs only)
- Gallery + provenance: `docs/gallery/`
- The one chart that travels well:
  `bench/results/2026-11-01-e8-turbo-int8-ck/quality_grid.png` (pairs,
  3 prompts × 3 seeds)

## Manual steps for the owner (not automatable via API)

- GitHub → Settings → Social preview → upload `assets/social-preview.png`
  (1280×640, <1 MB ✓)
- GitHub → tag `v0.1.0` + Release from `docs/releases/v0.1.0-rc1.md` after
  the two gated items close
