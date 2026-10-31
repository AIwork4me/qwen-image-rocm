import pytest


def test_build_workflow_nodes():
    from bench.comfyui_client import build_workflow

    wf = build_workflow(
        unet="qwen_image_2.1_bf16.safetensors",
        clip="qwen3vl_8b_bf16.safetensors",
        vae="qwen_image_2.1_vae_bf16.safetensors",
        prompt="a cat",
        negative="",
        width=1024,
        height=1024,
        steps=40,
        seed=42,
        sampler="euler",
        scheduler="simple",
    )
    classes = {nid: node["class_type"] for nid, node in wf.items()}
    assert set(classes.values()) >= {
        "UNETLoader",
        "CLIPLoader",
        "VAELoader",
        "CLIPTextEncode",
        "EmptyLatentImage",
        "KSampler",
        "VAEDecode",
        "SaveImage",
    }
    # two text encodes (positive + negative)
    assert list(classes.values()).count("CLIPTextEncode") == 2


def test_build_workflow_seed_mapping():
    from bench.comfyui_client import build_workflow

    wf = build_workflow(
        unet="u", clip="c", vae="v", prompt="p", negative="n",
        width=1024, height=1024, steps=40, seed=1337,
        sampler="euler", scheduler="simple",
    )
    ks = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
    assert ks["inputs"]["seed"] == 1337
    assert ks["inputs"]["steps"] == 40
    assert ks["inputs"]["sampler_name"] == "euler"
    assert ks["inputs"]["scheduler"] == "simple"
    assert ks["inputs"]["cfg"] == 1.0  # official Qwen-Image-2.1 default
    latent = [n for n in wf.values() if n["class_type"] == "EmptyLatentImage"][0]
    assert latent["inputs"]["width"] == 1024
    assert latent["inputs"]["height"] == 1024


def test_build_workflow_variant_params():
    from bench.comfyui_client import build_workflow

    wf = build_workflow(
        unet="u_int8.safetensors", clip="c_int8.safetensors", vae="v",
        prompt="p", negative="n", width=1024, height=1024, steps=8, seed=1,
        sampler="euler", scheduler="simple", cfg=2.5,
        weight_dtype="fp8_e4m3fn", tiled_vae=True,
    )
    ks = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
    assert ks["inputs"]["cfg"] == 2.5  # cfg recorded + wired (was hardcoded 1.0)
    assert ks["inputs"]["steps"] == 8
    unet = [n for n in wf.values() if n["class_type"] == "UNETLoader"][0]
    assert unet["inputs"]["weight_dtype"] == "fp8_e4m3fn"
    dec = [n for n in wf.values() if "VAEDecode" in n["class_type"]]
    assert [d["class_type"] for d in dec] == ["VAEDecodeTiled"]  # tiled switch
    assert dec[0]["inputs"]["tile_size"] == 512  # required in 0.43 (server default)


def _monitor_with_events(events, vram_peak=17000.0, residency=16000.0):
    from bench.comfyui_client import RunMonitor

    mon = RunMonitor.__new__(RunMonitor)  # no threads; pure summarize test
    mon.events = events
    mon.vram_peak_mb = vram_peak
    mon.vram_residency_mb = residency
    mon.monitor_error = None
    return mon


WF = {
    "unet_1": {"class_type": "UNETLoader", "inputs": {}},
    "pos_1": {"class_type": "CLIPTextEncode", "inputs": {}},
    "neg_1": {"class_type": "CLIPTextEncode", "inputs": {}},
    "ks_1": {"class_type": "KSampler", "inputs": {}},
    "dec_1": {"class_type": "VAEDecode", "inputs": {}},
}


def test_run_monitor_summarize_node_and_step_timing():
    events = [
        {"t": 0.0, "type": "execution_start", "data": {}},
        {"t": 1.0, "type": "executing", "data": {"node": "pos_1"}},
        {"t": 4.0, "type": "executing", "data": {"node": "ks_1"}},   # pos: 3.0s
        {"t": 4.5, "type": "progress", "data": {"value": 1, "max": 3, "node": "ks_1"}},
        {"t": 5.5, "type": "progress", "data": {"value": 2, "max": 3, "node": "ks_1"}},
        {"t": 6.5, "type": "progress", "data": {"value": 3, "max": 3, "node": "ks_1"}},
        {"t": 8.0, "type": "executing", "data": {"node": "dec_1"}},  # ks: 4.0s
        {"t": 9.0, "type": "executing", "data": {"node": None}},     # dec: 1.0s
    ]
    s = _monitor_with_events(events).summarize(WF)
    assert s["text_encode_s"] == 3.0
    assert s["ksampler_s"] == 4.0
    assert s["vae_decode_s"] == 1.0
    # step 1 = first progress - KSampler start; steps 2..3 = progress deltas
    assert s["step_times_s"] == [0.5, 1.0, 1.0]
    assert s["cached_nodes"] == []
    assert s["vram_peak_mb"] == 17000.0
    assert s["vram_residency_mb"] == 16000.0


def test_run_monitor_summarize_cached_nodes():
    # TE nodes were cache hits: 'execution_cached' lists them, no 'executing'
    events = [
        {"t": 0.0, "type": "execution_start", "data": {}},
        {"t": 0.1, "type": "execution_cached", "data": {"nodes": ["pos_1", "neg_1"]}},
        {"t": 0.2, "type": "executing", "data": {"node": "ks_1"}},
        {"t": 40.2, "type": "executing", "data": {"node": "dec_1"}},
        {"t": 41.2, "type": "executing", "data": {"node": None}},
    ]
    s = _monitor_with_events(events).summarize(WF)
    assert s["text_encode_s"] == 0.0  # cached = excluded (the v1.2 truth)
    assert len(s["cached_nodes"]) == 2
    assert any(n.startswith("CLIPTextEncode#") for n in s["cached_nodes"])
    assert s["ksampler_s"] == 40.0


def test_run_monitor_summarize_unterminated_node():
    # error path: last node never closed by an 'executing' None event
    events = [
        {"t": 0.0, "type": "executing", "data": {"node": "ks_1"}},
        {"t": 5.0, "type": "progress", "data": {"value": 1, "max": 2, "node": "ks_1"}},
        {"t": 6.0, "type": "execution_error", "data": {}},
    ]
    s = _monitor_with_events(events).summarize(WF)
    assert s["node_timings_s"]["KSampler#ks_1"] == 6.0  # closed at last event


def test_check_server_rejects_cpu(monkeypatch):
    from bench import comfyui_client as cc

    class FakeResp:
        def __init__(self, payload):
            self._p = payload

        def json(self):
            return self._p

    monkeypatch.setattr(
        cc, "_get", lambda url, timeout=10: FakeResp(
            {"devices": [{"name": "cpu", "type": "cpu"}]}
        )
    )
    with pytest.raises(RuntimeError, match="7900"):
        cc.check_server("http://127.0.0.1:8188")


def test_preflight_workflow_rejects_missing_node(monkeypatch):
    from bench import comfyui_client as cc

    # server only knows UNETLoader
    object_info = {
        "UNETLoader": {"input": {"required": {"unet_name": [["qwen.safetensors"]]}}},
    }

    class R:
        def __init__(self, code, payload):
            self.status_code = code
            self._p = payload

        def json(self):
            return self._p

    def fake_get(url, timeout=10):
        key = url.rsplit("/", 1)[-1]
        if key in object_info:
            return R(200, object_info[key])
        return R(404, {})

    monkeypatch.setattr(cc, "_get", fake_get)
    wf = cc.build_workflow(
        unet="qwen.safetensors", clip="c", vae="v", prompt="p", negative="",
        width=8, height=8, steps=1, seed=1, sampler="euler", scheduler="simple",
    )
    with pytest.raises(RuntimeError, match="not on server"):
        cc.preflight_workflow("http://x", wf)


def test_preflight_workflow_rejects_bad_model_name(monkeypatch):
    from bench import comfyui_client as cc

    wf = cc.build_workflow(
        unet="nope.safetensors", clip="c", vae="v", prompt="p", negative="",
        width=8, height=8, steps=1, seed=1, sampler="euler", scheduler="simple",
    )
    # server knows every class; only the unet enum check should fail
    object_info = {}
    for node in wf.values():
        object_info.setdefault(
            node["class_type"],
            {"input": {"required": {}}},
        )
    object_info["UNETLoader"] = {
        "input": {"required": {"unet_name": [["qwen.safetensors"]]}}
    }

    class R:
        def __init__(self, code, payload):
            self.status_code = code
            self._p = payload

        def json(self):
            return self._p

    monkeypatch.setattr(
        cc, "_get",
        lambda url, timeout=10: R(
            200, {url.rsplit("/", 1)[-1]: object_info[url.rsplit("/", 1)[-1]]}
        ),
    )
    with pytest.raises(RuntimeError, match="nope.safetensors"):
        cc.preflight_workflow("http://x", wf)


def test_post_prompt_surfaces_error_body(monkeypatch):
    from bench import comfyui_client as cc

    class FakePost:
        def __init__(self):
            self.status_code = 400
            self.text = (
                '{"error": {"type": "value_error",'
                ' "node_errors": {"KSampler": "bad input"}}}'
            )
            self.body = {}

        def raise_for_status(self):
            import requests

            raise requests.HTTPError("400")

    import requests

    monkeypatch.setattr(requests, "post", lambda *a, **k: FakePost())
    with pytest.raises(RuntimeError, match="node_errors"):
        cc.post_prompt("http://x", {"n": {"class_type": "X", "inputs": {}}})
