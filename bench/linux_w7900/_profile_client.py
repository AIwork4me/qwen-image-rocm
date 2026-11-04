
import json, sys, time, urllib.request

base = sys.argv[1]
out = {"events": []}

def post(path, body=None):
    req = urllib.request.Request(base + path,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def wait(prompt_id, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.loads(urllib.request.urlopen(f"{base}/history/{prompt_id}", timeout=30).read())
        if prompt_id in h:
            return h[prompt_id]
        time.sleep(0.5)
    raise TimeoutError(prompt_id)

def gen(prompt, seed, steps=40, tag=""):
    wf = {
        "unet": {"class_type": "UNETLoader",
                 "inputs": {"unet_name": "qwen_image_2.1_bf16.safetensors", "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader",
                 "inputs": {"clip_name": "qwen3vl_8b_bf16.safetensors", "type": "qwen_image"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["clip", 0]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["clip", 0]}},
        "latent": {"class_type": "EmptyLatentImage",
                   "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "ks": {"class_type": "KSampler",
               "inputs": {"seed": seed, "steps": steps, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
                          "model": ["unet", 0], "positive": ["pos", 0],
                          "negative": ["neg", 0], "latent_image": ["latent", 0]}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"filename_prefix": "qir_prof", "images": ["dec", 0]}},
    }
    t0 = time.perf_counter()
    pid = post("/prompt", {"prompt": wf})["prompt_id"]
    wait(pid)
    dt = time.perf_counter() - t0
    out["events"].append({"tag": tag, "seed": seed, "steps": steps,
                          "wall_s": round(dt, 3),
                          "t_monotonic_start": t0, "t_monotonic_end": time.perf_counter()})
    print(f"{tag}: {dt:.2f}s", flush=True)

P1 = "夕阳下的江南水乡小镇，石桥横跨河道，乌篷船缓缓驶过，白墙黛瓦的民居倒映在金色的河面上，远处炊烟袅袅，超高清摄影质感"

# args: base out mode window_start boot_s
mode = sys.argv[3]
WS = float(sys.argv[4])
BOOT = float(sys.argv[5])
t_client0 = time.perf_counter()
# timeline: cold (model loads) -> warmup -> sleep so the traced generation
# STARTS just after the rocprof collection window opens
gen(P1, 1000042, 40, "cold")
gen(P1, 2000042, 40, "warmup")
target = t_client0 + (WS - BOOT - 1.0)
delay = target - time.perf_counter()
if delay > 0:
    print(f"sleeping {delay:.1f}s to align with collection window", flush=True)
    time.sleep(delay)
if mode == "dit":
    gen(P1, 42, 40, "traced-warm")
else:  # "te": fresh prompt so the text encoder runs inside the window
    gen(P1 + " .", 43, 40, "traced-fresh")
json.dump(out, open(sys.argv[2], "w"), indent=1)
