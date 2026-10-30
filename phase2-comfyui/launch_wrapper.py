"""Launch wrapper for ComfyUI that applies the project's env-gated SDPA
workaround (QIR_SDP=math) BEFORE ComfyUI imports torch — see
docs/issues/2026-10-30-hiperrorinvalidvalue-qwen3vl-textencoder.md.
Run via launch_comfyui.ps1; extra CLI args pass through to ComfyUI main.py.
"""

import os
import runpy
import sys

COMFY_DIR = os.path.join(os.path.dirname(__file__), "ComfyUI")
COMFY_MAIN = os.path.join(COMFY_DIR, "main.py")
sys.path.insert(0, COMFY_DIR)  # runpy does not add the script's dir for `comfy`

if os.environ.get("QIR_SDP") == "math":
    import torch

    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    print("note: math-only SDP forced (QIR_SDP=math) before ComfyUI import")

sys.argv = [COMFY_MAIN] + sys.argv[1:]
runpy.run_path(COMFY_MAIN, run_name="__main__")
