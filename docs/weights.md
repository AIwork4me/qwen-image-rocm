# ComfyUI split-format weights (Phase 2)

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
