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
