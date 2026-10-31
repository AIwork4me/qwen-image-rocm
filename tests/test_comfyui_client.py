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
