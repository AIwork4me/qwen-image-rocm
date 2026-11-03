"""Phase 5 — heterogeneous & pipeline experiments on one W7900.

H1 (CPU TE feasibility): the Qwen3-VL 8B text encoder run on the EPYC CPU
via ComfyUI's own loader (comfy.sd.load_clip with load_device=cpu — the
same graph the server runs), vs the GPU. Measures load time, encode time
for the 3 frozen prompts, conditioning numerical agreement, and VRAM
residency difference (through a server-side CLIPLoader device=cpu run).

H2 (multi-request pipeline): 4 prompts, turbo 8-step. Arm A = sequential
(server-side GPU TE then gen, one request at a time). Arm B = CPU TE for
upcoming requests in a separate process overlapping GPU denoising of the
current request, injected through the lab-owned LinuxLabCondLoader custom
node. Overlap is proven with timestamps (never inferred).
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import lab_env

VENV_PY = lab_env.REPO / ".venv-linux-lab" / "bin" / "python"
TE_PATH = lab_env.REPO / "weights" / "comfyui-split" / "text_encoders" / "qwen3vl_8b_bf16.safetensors"
PROMPTS = {p["id"]: p["prompt"] for p in json.loads(
    (lab_env.REPO / "bench" / "prompts.json").read_text(encoding="utf-8"))["prompts"]}

CUSTOM_NODE = '''
"""Lab-owned custom node (linux_w7900): load precomputed conditioning.

Used ONLY by the H2 pipelined arm: a CPU text-encoder worker writes the
conditioning tensor to disk; the generation workflow loads it here so the
GPU never pays the TE cost. Not part of any benchmarked-quality path.
"""
import torch


class LinuxLabCondLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"cond_path": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "load"
    CATEGORY = "linux_w7900"

    def load(self, cond_path):
        blob = torch.load(cond_path, map_location="cpu", weights_only=True)
        cond = blob["cond"]
        if blob.get("device") == "cuda":
            cond = cond.to("cuda")
        return ([[cond, {}]],)


NODE_CLASS_MAPPINGS = {"LinuxLabCondLoader": LinuxLabCondLoader}
NODE_DISPLAY_NAME_MAPPINGS = {"LinuxLabCondLoader": "Linux Lab Cond Loader (H2)"}
'''

CPU_TE_WORKER = r'''
import sys, time
sys.path.insert(0, "/workspace/qwen-image-rocm/phase2-comfyui/ComfyUI")
import torch

text, out_path = sys.argv[1], sys.argv[2]
import comfy.sd
import comfy.model_management as mm

t0 = time.perf_counter()
clip = comfy.sd.load_clip(
    ckpt_paths=["/workspace/qwen-image-rocm/weights/comfyui-split/text_encoders/qwen3vl_8b_bf16.safetensors"],
    embedding_directory="/workspace/qwen-image-rocm/phase2-comfyui/ComfyUI/models/embeddings",
    clip_type=comfy.sd.CLIPType.QWEN_IMAGE,
    model_options={"load_device": torch.device("cpu"),
                   "offload_device": torch.device("cpu")})
load_s = time.perf_counter() - t0

t0 = time.perf_counter()
tokens = clip.tokenize(text)
tok_s = time.perf_counter() - t0
t0 = time.perf_counter()
cond = clip.encode_from_tokens_scheduled(tokens)
enc_s = time.perf_counter() - t0

torch.save({"cond": cond.cpu(), "device": "cuda"}, out_path)
import os
print(json.dumps if False else "", file=sys.stderr)
import json
meta = {"load_s": round(load_s, 2), "tokenize_s": round(tok_s, 4),
        "encode_s": round(enc_s, 3), "shape": list(cond.shape),
        "dtype": str(cond.dtype), "file_bytes": os.path.getsize(out_path)}
json.dump(meta, open(out_path + ".meta.json", "w"), indent=1)
print(json.dumps(meta))
'''


def install_custom_node() -> Path:
    d = lab_env.COMFY_DIR / "custom_nodes" / "linux_w7900_lab"
    d.mkdir(parents=True, exist_ok=True)
    (d / "__init__.py").write_text(CUSTOM_NODE, encoding="utf-8")
    return d


def run_h1(date: str | None = None) -> Path:
    date = date or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = lab_env.RESULTS_ROOT / f"{date}-H1-cpu-te"
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {"experiment": "H1", "date": date}

    # -- direct probe: same loader the server uses, GPU vs CPU ------------
    probe = r'''
import sys, json, time
sys.path.insert(0, "/workspace/qwen-image-rocm/phase2-comfyui/ComfyUI")
import torch
import comfy.sd

PROMPTS = json.load(open("/workspace/qwen-image-rocm/bench/prompts.json"))
texts = {p["id"]: p["prompt"] for p in PROMPTS["prompts"]}
TE = "/workspace/qwen-image-rocm/weights/comfyui-split/text_encoders/qwen3vl_8b_bf16.safetensors"
EMB = "/workspace/qwen-image-rocm/phase2-comfyui/ComfyUI/models/embeddings"

out = {}
conds = {}
for device in ("cuda", "cpu"):
    tag = "gpu" if device == "cuda" else "cpu"
    try:
        t0 = time.perf_counter()
        clip = comfy.sd.load_clip(
            ckpt_paths=[TE], embedding_directory=EMB,
            clip_type=comfy.sd.CLIPType.QWEN_IMAGE,
            model_options={"load_device": torch.device(device),
                           "offload_device": torch.device(device)})
        load_s = time.perf_counter() - t0
        enc = {}
        for pid, text in texts.items():
            t0 = time.perf_counter()
            tokens = clip.tokenize(text)
            tok_s = time.perf_counter() - t0
            t0 = time.perf_counter()
            cond = clip.encode_from_tokens_scheduled(tokens)
            if device == "cuda":
                torch.cuda.synchronize()
            enc_s = time.perf_counter() - t0
            enc[pid] = {"tokenize_s": round(tok_s, 4),
                        "encode_s": round(enc_s, 3),
                        "shape": list(cond.shape), "dtype": str(cond.dtype)}
            conds.setdefault(pid, {})[tag] = cond.detach().float().cpu()
        out[tag] = {"load_s": round(load_s, 2), "encode": enc}
        if device == "cuda":
            out[tag]["vram_allocated_mb"] = round(torch.cuda.memory_allocated() / 2**20, 1)
        del clip
        if device == "cuda":
            torch.cuda.empty_cache()
    except Exception as exc:  # noqa: BLE001
        out[tag] = {"error": repr(exc)[:400]}

# numerical agreement gpu vs cpu
agree = {}
for pid, pair in conds.items():
    if "gpu" in pair and "cpu" in pair:
        g, c = pair["gpu"], pair["cpu"]
        if g.shape == c.shape:
            agree[pid] = {
                "max_abs_diff": round((g - c).abs().max().item(), 5),
                "mean_abs_diff": round((g - c).abs().mean().item(), 6),
                "cosine": round(torch.nn.functional.cosine_similarity(
                    g.flatten().unsqueeze(0), c.flatten().unsqueeze(0)).item(), 6),
            }
        else:
            agree[pid] = {"shape_mismatch": [list(g.shape), list(c.shape)]}
out["agreement_gpu_vs_cpu"] = agree
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(out, indent=1))
'''
    script = out_dir / "_h1_probe.py"
    script.write_text(probe, encoding="utf-8")
    r = subprocess.run([str(VENV_PY), "-I", str(script), str(out_dir / "h1_probe.json")],
                       capture_output=True, text=True, timeout=3600, cwd=str(lab_env.REPO))
    (out_dir / "h1_stdout.log").write_text(r.stdout[-30000:], encoding="utf-8")
    (out_dir / "h1_stderr.log").write_text(r.stderr[-30000:], encoding="utf-8")
    try:
        results["probe"] = json.loads((out_dir / "h1_probe.json").read_text())
    except (OSError, ValueError):
        results["probe"] = {"status": "FAIL", "stderr_tail": r.stderr[-1500:]}
    print(r.stdout[-2500:])

    # -- server-side integrated variant: CLIPLoader device=cpu (VRAM view) --
    try:
        from .. import comfyui_client
        from .server import ComfyServer

        server = ComfyServer(port=8188, log_path=out_dir / "server.log")
        server.start()
        try:
            base = server.base_url

            def te_wf(prompt: str, cpu: bool) -> dict:
                wf = comfyui_client.build_workflow(
                    unet="qwen_image_2.1_turbo_bf16.safetensors",
                    clip="qwen3vl_8b_bf16.safetensors",
                    vae="qwen_image_2.1_vae_bf16.safetensors",
                    prompt=prompt, negative="", width=1024, height=1024,
                    steps=8, seed=4242, sampler="euler", scheduler="simple")
                # flip the CLIPLoader to the requested device
                for node in wf.values():
                    if node["class_type"] == "CLIPLoader" and cpu:
                        node["inputs"]["device"] = "cpu"
                return wf

            integrated = {}
            for cpu in (False, True):
                tag = "clip_cpu" if cpu else "clip_gpu"
                # fresh text per run so TE is never a node-cache hit
                mon = comfyui_client.RunMonitor(base)
                mon.start()
                t0 = time.perf_counter()
                pid = comfyui_client.post_prompt(
                    base, te_wf(PROMPTS["p1-zh-scene"] + (" ." if not cpu else " !"), cpu),
                    client_id=mon.client_id)
                comfyui_client.wait_for_result(base, pid)
                wall = time.perf_counter() - t0
                mon.stop()
                s = mon.summarize(te_wf("", cpu))
                integrated[tag] = {
                    "total_s": round(wall, 3),
                    "text_encode_s": s["text_encode_s"],
                    "vram_peak_mb": s["vram_peak_mb"],
                    "vram_residency_mb": s["vram_residency_mb"],
                }
            results["integrated"] = integrated
        finally:
            server.stop()
    except Exception as exc:  # noqa: BLE001
        results["integrated"] = {"status": "FAIL", "error": repr(exc)[:400]}

    (out_dir / "H1_RESULTS.json").write_text(json.dumps(results, indent=2),
                                             encoding="utf-8")
    print(f"H1 results: {out_dir / 'H1_RESULTS.json'}")
    return out_dir


H2_PROMPTS = [
    ("req1", PROMPTS["p1-zh-scene"]),
    ("req2", PROMPTS["p2-en-scene"]),
    ("req3", PROMPTS["p3-poster-text"]),
    ("req4", "清晨的竹林小径，薄雾弥漫，阳光透过竹叶洒下斑驳光影，一条小溪蜿蜒流过，超高清摄影质感"),
]


def run_h2(date: str | None = None, port: int = 8188) -> Path:
    date = date or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = lab_env.RESULTS_ROOT / f"{date}-H2-pipeline"
    out_dir.mkdir(parents=True, exist_ok=True)
    install_custom_node()

    from .. import comfyui_client
    from .server import ComfyServer

    results: dict = {"experiment": "H2", "date": date,
                     "design": ("A: sequential server-side GPU TE + gen, one at a "
                                "time. B: CPU TE worker (separate process) for "
                                "upcoming requests overlapping GPU denoise; cond "
                                "injected via LinuxLabCondLoader.")}

    server = ComfyServer(port=port, log_path=out_dir / "server.log")
    server.start()
    try:
        base = server.base_url

        def wf_gpu_te(prompt: str, seed: int) -> dict:
            return comfyui_client.build_workflow(
                unet="qwen_image_2.1_turbo_bf16.safetensors",
                clip="qwen3vl_8b_bf16.safetensors",
                vae="qwen_image_2.1_vae_bf16.safetensors",
                prompt=prompt, negative="", width=1024, height=1024,
                steps=8, seed=seed, sampler="euler", scheduler="simple")

        def wf_precomputed_cond(cond_path: str, seed: int) -> dict:
            """Same generation graph, but conditioning comes from the file."""
            wf = wf_gpu_te("", seed)
            pos = neg = None
            for nid, node in wf.items():
                if node["class_type"] == "CLIPTextEncode":
                    if node["inputs"]["text"] == "":
                        (pos, neg) = (nid, pos) if pos is None else (pos, nid)
            for nid, node in list(wf.items()):
                if node["class_type"] == "CLIPTextEncode":
                    # replace BOTH pos and neg with file-loaded cond
                    # (negative prompt is empty; cfg=1 ignores it anyway)
                    wf[nid] = {"class_type": "LinuxLabCondLoader",
                               "inputs": {"cond_path": cond_path}}
            # drop the now-unused CLIPLoader to keep VRAM comparable? keep it:
            # the A arm has it loaded too (fairness).
            return wf

        def drain():
            import requests

            time.sleep(0.3)
            while True:
                q = requests.get(f"{base}/queue", timeout=10).json()
                if not q.get("queue_running") and not q.get("queue_pending"):
                    return
                time.sleep(0.3)

        # warm the models once (steady-state service assumption)
        t0 = time.perf_counter()
        pid = comfyui_client.post_prompt(base, wf_gpu_te(H2_PROMPTS[0][1], seed=999999))
        comfyui_client.wait_for_result(base, pid)
        results["warmup_s"] = round(time.perf_counter() - t0, 3)
        drain()

        # ---------------- Arm A: sequential ------------------------------
        events_a = []
        t_all = time.perf_counter()
        for name, prompt in H2_PROMPTS:
            t0 = time.perf_counter()
            pid = comfyui_client.post_prompt(base, wf_gpu_te(prompt, seed=42))
            comfyui_client.wait_for_result(base, pid)
            events_a.append({"req": name, "wall_s": round(time.perf_counter() - t0, 3)})
        results["A_sequential"] = {
            "events": events_a,
            "total_s": round(time.perf_counter() - t_all, 3),
            "images_per_min": round(4 * 60 / (time.perf_counter() - t_all), 2),
        }

        # ---------------- Arm B: pipelined --------------------------------
        import concurrent.futures as cf

        worker = out_dir / "_cpu_te_worker.py"
        worker.write_text(CPU_TE_WORKER, encoding="utf-8")

        def cpu_te(prompt_text: str) -> dict:
            cond_path = out_dir / f"cond-{abs(hash(prompt_text)) % 10**8}.pt"
            t0 = time.perf_counter()
            r = subprocess.run([str(VENV_PY), "-I", str(worker), prompt_text,
                                str(cond_path)], capture_output=True, text=True,
                               timeout=900)
            wall = time.perf_counter() - t0
            if r.returncode != 0:
                raise RuntimeError(f"cpu TE failed: {r.stderr[-800:]}")
            meta = json.loads((Path(str(cond_path) + ".meta.json")).read_text())
            meta["wall_s"] = round(wall, 3)
            meta["cond_path"] = str(cond_path)
            meta["t_start"] = t0
            meta["t_end"] = time.perf_counter()
            return meta

        events_b = []
        overlap_intervals = []
        t_all = time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=1) as pool:
            # pipeline fill: req1's CPU TE runs alone (nothing to overlap yet)
            te1 = cpu_te(H2_PROMPTS[0][1])
            events_b.append({"req": "req1", "cpu_te_s": te1["wall_s"],
                             "encode_s": te1["encode_s"]})
            fut = None
            for i in range(1, 5):
                if fut is not None:
                    te_next = fut.result()  # TE for request i (already running)
                else:
                    te_next = te1
                gen_cond = te_next
                t0 = time.perf_counter()
                pid = comfyui_client.post_prompt(
                    base, wf_precomputed_cond(gen_cond["cond_path"], seed=42))
                # start CPU TE for request i+1 (overlaps this generation)
                fut = pool.submit(cpu_te, H2_PROMPTS[i][1]) if i < 4 else None
                comfyui_client.wait_for_result(base, pid)
                gen_end = time.perf_counter()
                ev = {"req": H2_PROMPTS[i - 1][0],
                      "gen_wall_s": round(gen_end - t0, 3)}
                if fut is not None:
                    te_after = fut.result()
                    ev["cpu_te_next_s"] = te_after["wall_s"]
                    ev["cpu_te_next_encode_s"] = te_after["encode_s"]
                    # overlap = intersection of [t0, gen_end] and TE window
                    o = max(0.0, min(gen_end, te_after["t_end"])
                            - max(t0, te_after["t_start"]))
                    ev["actual_overlap_s"] = round(o, 3)
                    overlap_intervals.append(o)
                    fut = None
                events_b.append(ev)
        total_b = time.perf_counter() - t_all
        results["B_pipelined"] = {
            "events": events_b,
            "total_s": round(total_b, 3),
            "images_per_min": round(4 * 60 / total_b, 2),
            "overlap_s_total": round(sum(overlap_intervals), 3),
            "overlap_proven": sum(overlap_intervals) > 1.0,
        }
    finally:
        server.stop()

    (out_dir / "H2_RESULTS.json").write_text(json.dumps(results, indent=2),
                                             encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if k != "design"}, indent=1))
    print(f"H2 results: {out_dir / 'H2_RESULTS.json'}")
    return out_dir
