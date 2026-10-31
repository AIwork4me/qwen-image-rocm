# ComfyUI split-format weights (Phase 2 + Phase 3)

ModelScope check (2026-10-31): `Comfy-Org/Qwen-Image-2.1` exists on
ModelScope but is an **empty shell** (0 files; download transfers nothing)
→ engaged the pre-approved HF fallback. Direct huggingface.co is unreachable
from this network, so the endpoint mirror was used:

```
$env:HF_ENDPOINT = "https://hf-mirror.com"
hf download Comfy-Org/Qwen-Image-2.1 `
  --include diffusion_models/qwen_image_2.1_bf16.safetensors `
            text_encoders/qwen3vl_8b_bf16.safetensors `
            vae/qwen_image_2.1_vae_bf16.safetensors `
  --local-dir weights/comfyui-split
```

bf16 baseline files (~30 GB total):

```
weights/comfyui-split/
├── diffusion_models/qwen_image_2.1_bf16.safetensors   (7B DiT, bf16)
├── text_encoders/qwen3vl_8b_bf16.safetensors           (8B text encoder)
└── vae/qwen_image_2.1_vae_bf16.safetensors
```

Mapped into ComfyUI via `phase2-comfyui/extra_model_paths.yaml`. Quantized
variants (int8_convrot, w4a8) and the Turbo checkpoint are NOT downloaded
in Phase 2 — they are Phase 3 material.

## Phase 3 variants (2026-10-31)

Repo tree (verified via hf-mirror API): **no fp8 DiT exists for
Qwen-Image-2.1** — DiT = bf16 / int8_convrot / turbo_bf16 / turbo_int8_convrot;
TE = bf16 / int8_convrot (9.4GB) / w4a8 (6.3GB); VAE = bf16 only.
Native quantized checkpoints load via the plain UNETLoader/CLIPLoader with
`weight_dtype: default` (`.comfy_quant` metadata auto-detected) — no custom
nodes. Downloaded for E1/E2:

```
diffusion_models/qwen_image_2.1_turbo_bf16.safetensors       (14.23 GB, E1)
diffusion_models/qwen_image_2.1_int8_convrot.safetensors     (7.26 GB, E2)
text_encoders/qwen3vl_8b_int8_convrot.safetensors            (9.4 GB, E2)
text_encoders/qwen3vl_8b_w4a8.safetensors                     (6.3 GB, E2)
diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors (7.26 GB, E2)
```

### Download-tooling lesson (measured 2026-10-31, mainland network)

1. `hf download` gets 40 MB/s via parallel chunks, but its `.incomplete`
   part files **never resume after a forceful kill** — a stall-watchdog
   that kills hf restarts a fresh part set every time (~38 GB of duplicate
   partials for ~8 GB of progress before this was caught).
2. Single `curl -C -` resumes byte-exact but the mirror throttles one
   connection to ~150 KB/s at peak hours (40 h ETA for 13 GB).
3. Working tool: `tools/download_parallel.py` — N concurrent ranged
   requests (default 16), each chunk resuming byte-exact on its own part
   file; kill/restart at any time. Measured 8–20+ MB/s aggregate:

```
phase2-comfyui/.venv/Scripts/python.exe -I tools/download_parallel.py `
  https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/<path> `
  weights/comfyui-split/<path> 16
```

`tools/download_weights.ps1` (curl `-C -` sequential) remains for small
files; LPIPS reference weights are exempt from the ModelScope-first rule
(design doc) and were fetched from jsdelivr/ghproxy mirrors because
raw.githubusercontent.com is blocked on this network.

**Notes for mainland-China networks** (measured 2026-10-31):

1. `hf download` via hf-mirror with the default **hf-xet** protocol hangs
   at 0 bytes — the xet CAS endpoints are not proxied by hf-mirror.
   Fix: `HF_HUB_DISABLE_XET=1` (plain HTTPS via the mirror; observed
   40 MB/s bursts).
2. Even on plain HTTPS the mirror connection dies mid-transfer every few
   GB **without exiting** — wrap the download in a watchdog that kills
   and restarts it on 5-minute stalls (`hf download` resumes
   `.incomplete` files, so restarts are cheap).

---

# Weights (Phase 1, diffusers format)

Downloaded from ModelScope (weights are NOT committed to this repo):

```
modelscope download --model Qwen/Qwen-Image-2.1 --local_dir weights/diffusers-format
```

## Expected layout (verified 2026-10-30, ~30.9 GB total)

```
weights/diffusers-format/
├── model_index.json
├── processor/                 # Qwen3-VL preprocessor configs
├── scheduler/scheduler_config.json
├── text_encoder/              # Qwen3-VL 8B, bf16
│   ├── model-00001-of-00004.safetensors   4.65 GB
│   ├── model-00002-of-00004.safetensors   4.58 GB
│   ├── model-00003-of-00004.safetensors   4.58 GB
│   ├── model-00004-of-00004.safetensors   2.52 GB
│   └── model.safetensors.index.json
├── transformer/               # 7B single-stream DiT, bf16
│   ├── diffusion_pytorch_model-00001-of-00002.safetensors   9.28 GB
│   ├── diffusion_pytorch_model-00002-of-00002.safetensors   3.97 GB
│   └── diffusion_pytorch_model.safetensors.index.json
└── vae/
    └── diffusion_pytorch_model.safetensors   1.26 GB
```

Plus tokenizer files (`vocab.json`, `merges.txt`, `tokenizer.json`, ...)
and configs. bf16 total exceeds the 7900 XTX's 24 GB VRAM, so the pipeline
runs with `enable_model_cpu_offload()`.
