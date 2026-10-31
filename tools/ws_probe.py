"""Diagnostic: connect to ComfyUI /ws and print raw event flow for one tiny
prompt (256x256, 2 steps). Verifies event types + parameter spelling.

Run with the server up:
  uv run --python 3.12 --with websocket-client --with requests python -I tools/ws_probe.py
"""

import json
import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import websocket  # noqa: E402

BASE = "http://127.0.0.1:8188"


def main() -> None:
    import requests

    from bench.comfyui_client import build_workflow, check_server, post_prompt, wait_for_result

    check_server(BASE)
    cid = uuid.uuid4().hex
    url = f"ws://127.0.0.1:8188/ws?clientId={cid}"
    print(f"connecting {url}")
    ws = websocket.create_connection(url, timeout=5)
    ws.settimeout(1.0)
    done = threading.Event()
    count = {"n": 0}

    def reader():
        while not done.is_set():
            try:
                op, data = ws.recv_data()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as exc:  # noqa: BLE001
                print("reader exit:", exc)
                return
            if op != 1:
                print(f"[binary opcode={op} len={len(data)}]")
                continue
            msg = json.loads(data.decode("utf-8"))
            count["n"] += 1
            print(f"{time.perf_counter():10.2f} {msg.get('type'):20s} "
                  f"{str(msg.get('data'))[:110]}", flush=True)
            if msg.get("type") in ("execution_success", "execution_error"):
                done.set()
                return

    threading.Thread(target=reader, daemon=True).start()

    wf = build_workflow(
        unet="qwen_image_2.1_bf16.safetensors",
        clip="qwen3vl_8b_bf16.safetensors",
        vae="qwen_image_2.1_vae_bf16.safetensors",
        prompt="a cat", negative="", width=256, height=256,
        steps=2, seed=1, sampler="euler", scheduler="simple",
    )
    t0 = time.perf_counter()
    pid = post_prompt(BASE, wf, client_id=cid)
    print(f"submitted {pid}; waiting...")
    wait_for_result(BASE, pid, timeout_s=900)
    done.wait(timeout=30)
    print(f"done in {time.perf_counter() - t0:.1f}s; events received: {count['n']}")


if __name__ == "__main__":
    main()
