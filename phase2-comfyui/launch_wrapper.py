"""Launch wrapper for ComfyUI that applies the project's env-gated SDPA
workaround BEFORE ComfyUI imports torch — see
docs/issues/2026-10-30-hiperrorinvalidvalue-qwen3vl-textencoder.md.
Run via launch_comfyui.ps1; extra CLI args pass through to ComfyUI main.py.

QIR_SDP modes:
- "math"     : disable flash + mem-efficient SDPA before ComfyUI import.
- "math-hard": same, PLUS neuter any later re-enable. Required when ComfyUI
               runs with --use-pytorch-cross-attention: its flag handler
               calls enable_flash_sdp(True)/enable_mem_efficient_sdp(True)
               (model_management.py:547-550), silently undoing the plain
               math workaround and re-arming the hipErrorInvalidValue path.
"""

import os
import runpy
import sys

COMFY_DIR = os.path.join(os.path.dirname(__file__), "ComfyUI")
COMFY_MAIN = os.path.join(COMFY_DIR, "main.py")
sys.path.insert(0, COMFY_DIR)  # runpy does not add the script's dir for `comfy`

mode = os.environ.get("QIR_SDP", "")
if mode in ("math", "math-hard"):
    import torch

    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    print(f"note: math-only SDP forced (QIR_SDP={mode}) before ComfyUI import")
    if mode == "math-hard":
        _orig_flash = torch.backends.cuda.enable_flash_sdp
        _orig_mem = torch.backends.cuda.enable_mem_efficient_sdp

        def _block_reenable(name, orig, enable):
            if enable:
                print(f"note: math-hard blocked re-enable of {name} SDPA")
                return
            orig(enable)

        torch.backends.cuda.enable_flash_sdp = lambda e: _block_reenable(
            "flash", _orig_flash, e)
        torch.backends.cuda.enable_mem_efficient_sdp = lambda e: _block_reenable(
            "mem-efficient", _orig_mem, e)

sys.argv = [COMFY_MAIN] + sys.argv[1:]
runpy.run_path(COMFY_MAIN, run_name="__main__")
