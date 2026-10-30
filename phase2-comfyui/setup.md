# Phase 2 environment (ComfyUI)

- ComfyUI commit (pinned, depth-1 clone): `b5a432157de6b8884f81104cd02926adf4d597e4`
- venv: `phase2-comfyui/.venv` (CPython 3.12.16, uv --seed pip)
- torch stack: installed with the mandated AMD command (verbatim), then
  ComfyUI `requirements.txt`; post-install assert passed
  (`torch==2.12.0+rocm7.14.1`, torchvision 0.27.0, HIP 7.14.60850)
- Notable resolved versions: transformers 5.22.1 (same as Phase 1),
  comfyui-frontend-package 1.57.6, safetensors 0.8.0

## Launch

`phase2-comfyui/launch_comfyui.ps1 -Port 8188` (sets `QIR_SDP=math`
workaround env honored by `launch_wrapper.py`, listens on 127.0.0.1,
uses `extra_model_paths.yaml` for weights).

Default-attention behavior (no workaround) is tested in the smoke task;
see docs/issues/ for whatever it hits.
